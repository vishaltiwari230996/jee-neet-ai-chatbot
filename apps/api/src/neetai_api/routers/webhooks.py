"""Webhook endpoints for third-party product events."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from neetai_api.container import Container
from neetai_api.deps import get_container
from neetai_api.integrations.google_sheets import GoogleSheetsClient, SignupSheetRow
from neetai_api.logging import get_logger
from neetai_api.settings import Settings, get_settings
from neetai_core.ids import StudentId
from neetai_ports import Student

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
log = get_logger("neetai_api.webhooks")


SettingsDep = Annotated[Settings, Depends(get_settings)]
ContainerDep = Annotated[Container, Depends(get_container)]


class WebhookAck(BaseModel):
    ok: bool = True
    ignored: bool = False
    reason: str | None = None


@router.post(
    "/clerk",
    response_model=WebhookAck,
    status_code=status.HTTP_200_OK,
    summary="Receive Clerk user lifecycle events.",
)
async def clerk_webhook(
    request: Request,
    settings: SettingsDep,
    container: ContainerDep,
) -> WebhookAck:
    body = await request.body()
    _verify_clerk_signature(
        body=body,
        headers=request.headers,
        signing_secret=settings.clerk_webhook_signing_secret,
    )

    event = json.loads(body)
    event_type = event.get("type")
    if event_type != "user.created":
        return WebhookAck(ignored=True, reason=f"ignored {event_type}")

    signup = _signup_from_clerk_event(event)
    await container.students.upsert(
        Student(
            student_id=StudentId(signup.student_id),
            email=signup.email,
            display_name=_display_name(signup.first_name, signup.last_name),
            created_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
        ),
    )

    if settings.signup_sheet_id:
        sheets = GoogleSheetsClient(
            spreadsheet_id=settings.signup_sheet_id,
            tab_name=settings.signup_sheet_tab_name,
            service_account_file=settings.google_service_account_file,
            service_account_json=settings.google_service_account_json,
        )
        await sheets.append_signup(signup)
    else:
        log.warning("signup.sheet.disabled", student_id=signup.student_id)

    log.info("signup.recorded", student_id=signup.student_id, email=signup.email)
    return WebhookAck()


def _verify_clerk_signature(
    *,
    body: bytes,
    headers: Mapping[str, str],
    signing_secret: str | None,
) -> None:
    if not signing_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_WEBHOOK_SIGNING_SECRET is not configured",
        )

    msg_id = headers.get("svix-id")
    timestamp = headers.get("svix-timestamp")
    signature_header = headers.get("svix-signature")
    if not msg_id or not timestamp or not signature_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature")

    now = int(time.time())
    try:
        sent_at = int(timestamp)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature timestamp",
        ) from exc
    if abs(now - sent_at) > 5 * 60:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stale signature")

    secret = signing_secret.removeprefix("whsec_")
    key = _b64decode(secret)
    signed = f"{msg_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()

    signatures = [
        part.split(",", maxsplit=1)[1]
        for part in signature_header.split(" ")
        if part.startswith("v1,")
    ]
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.b64decode(padded)


def _signup_from_clerk_event(event: dict[str, Any]) -> SignupSheetRow:
    data = event.get("data") or {}
    clerk_user_id = str(data["id"])
    email = _primary_email(data)
    created_at = _created_at(data)
    return SignupSheetRow(
        created_at=created_at,
        student_id=f"stu_{clerk_user_id}",
        clerk_user_id=clerk_user_id,
        email=email,
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
    )


def _primary_email(data: dict[str, Any]) -> str:
    primary_id = data.get("primary_email_address_id")
    emails = data.get("email_addresses") or []
    for email in emails:
        if email.get("id") == primary_id:
            return str(email.get("email_address") or "")
    if emails:
        return str(emails[0].get("email_address") or "")
    return ""


def _created_at(data: dict[str, Any]) -> str:
    created_ms = data.get("created_at")
    if isinstance(created_ms, int):
        return datetime.fromtimestamp(created_ms / 1000, tz=UTC).isoformat()
    return datetime.now(UTC).isoformat()


def _display_name(first_name: str | None, last_name: str | None) -> str | None:
    name = " ".join(part for part in (first_name, last_name) if part)
    return name or None
