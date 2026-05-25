"""Google Sheets append client.

Used by signup webhooks to keep a lightweight operational record of new
students outside the product database. Credentials are read from environment
or an ignored local file, never from source code.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

_SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)

_SIGNUP_HEADERS = [
    "created_at",
    "student_id",
    "clerk_user_id",
    "email",
    "first_name",
    "last_name",
    "exam_target",
    "class_level",
    "source",
]


@dataclass(slots=True, frozen=True)
class SignupSheetRow:
    created_at: str
    student_id: str
    clerk_user_id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    exam_target: str | None = None
    class_level: str | None = None
    source: str = "clerk_user_created"

    def to_values(self) -> list[str]:
        return [
            self.created_at,
            self.student_id,
            self.clerk_user_id,
            self.email,
            self.first_name or "",
            self.last_name or "",
            self.exam_target or "",
            self.class_level or "",
            self.source,
        ]


class GoogleSheetsClient:
    def __init__(
        self,
        *,
        spreadsheet_id: str,
        tab_name: str,
        service_account_file: str | None = None,
        service_account_json: str | None = None,
    ) -> None:
        self._spreadsheet_id = spreadsheet_id
        self._tab_name = tab_name
        self._session = _authorized_session(
            service_account_file=service_account_file,
            service_account_json=service_account_json,
        )

    async def append_signup(self, row: SignupSheetRow) -> None:
        await asyncio.to_thread(self._append_signup_sync, row)

    def _append_signup_sync(self, row: SignupSheetRow) -> None:
        self._ensure_headers_sync()
        range_name = quote(f"{self._tab_name}!A:I", safe="")
        url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{self._spreadsheet_id}/values/{range_name}:append"
            "?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
        )
        response = self._session.post(url, json={"values": [row.to_values()]}, timeout=20)
        response.raise_for_status()

    def _ensure_headers_sync(self) -> None:
        range_name = quote(f"{self._tab_name}!A1:I1", safe="")
        url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{self._spreadsheet_id}/values/{range_name}"
        )
        response = self._session.get(url, timeout=20)
        response.raise_for_status()
        values = response.json().get("values", [])
        if values and values[0] == _SIGNUP_HEADERS:
            return

        response = self._session.put(
            url + "?valueInputOption=RAW",
            json={"values": [_SIGNUP_HEADERS]},
            timeout=20,
        )
        response.raise_for_status()


def _authorized_session(
    *,
    service_account_file: str | None,
    service_account_json: str | None,
) -> AuthorizedSession:
    if service_account_json:
        info: dict[str, Any] = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
            info,
            scopes=_SCOPES,
        )
        return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]

    if service_account_file:
        credentials = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
            str(Path(service_account_file).expanduser()),
            scopes=_SCOPES,
        )
        return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]

    raise RuntimeError(
        "Google Sheets integration requires GOOGLE_SERVICE_ACCOUNT_FILE "
        "or GOOGLE_SERVICE_ACCOUNT_JSON",
    )
