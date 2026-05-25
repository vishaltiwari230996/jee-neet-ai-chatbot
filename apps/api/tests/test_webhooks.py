from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest
from fastapi import FastAPI

from neetai_api.settings import (
    AppEnv,
    DatabaseBackend,
    LLMProvider,
    LogFormat,
    Settings,
    get_settings,
)
from neetai_core.ids import StudentId

_SECRET = "whsec_" + base64.b64encode(b"test-secret").decode().rstrip("=")


@pytest.mark.asyncio
async def test_clerk_user_created_upserts_student(app: FastAPI) -> None:
    settings = Settings(
        env=AppEnv.LOCAL,
        llm_provider=LLMProvider.FAKE,
        database_backend=DatabaseBackend.MEMORY,
        log_format=LogFormat.TEXT,
        clerk_webhook_signing_secret=_SECRET,
        signup_sheet_id=None,
        google_service_account_file=None,
        google_service_account_json=None,
    )
    app.dependency_overrides[get_settings] = lambda: settings

    event = {
        "type": "user.created",
        "data": {
            "id": "user_123",
            "created_at": 1_700_000_000_000,
            "first_name": "Vishal",
            "last_name": "Tiwari",
            "primary_email_address_id": "email_1",
            "email_addresses": [
                {"id": "email_1", "email_address": "vishal@example.com"},
            ],
        },
    }
    body = json.dumps(event, separators=(",", ":")).encode()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/webhooks/clerk",
            content=body,
            headers=_signature_headers(body),
        )

    assert response.status_code == 200, response.text
    student = await app.state.container.students.get(StudentId("stu_user_123"))
    assert student is not None
    assert student.email == "vishal@example.com"
    assert student.display_name == "Vishal Tiwari"


@pytest.mark.asyncio
async def test_clerk_webhook_rejects_bad_signature(app: FastAPI) -> None:
    settings = Settings(
        env=AppEnv.LOCAL,
        llm_provider=LLMProvider.FAKE,
        database_backend=DatabaseBackend.MEMORY,
        log_format=LogFormat.TEXT,
        clerk_webhook_signing_secret=_SECRET,
        signup_sheet_id=None,
        google_service_account_file=None,
        google_service_account_json=None,
    )
    app.dependency_overrides[get_settings] = lambda: settings

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/webhooks/clerk",
            content=b'{"type":"user.created","data":{"id":"user_bad"}}',
            headers={
                "svix-id": "msg_1",
                "svix-timestamp": str(int(time.time())),
                "svix-signature": "v1,not-valid",
            },
        )

    assert response.status_code == 401, response.text


def _signature_headers(body: bytes) -> dict[str, str]:
    msg_id = "msg_1"
    timestamp = str(int(time.time()))
    signed = f"{msg_id}.{timestamp}.".encode() + body
    digest = hmac.new(b"test-secret", signed, hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode()
    return {
        "svix-id": msg_id,
        "svix-timestamp": timestamp,
        "svix-signature": f"v1,{signature}",
        "content-type": "application/json",
    }
