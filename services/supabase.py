"""Supabase HTTPS client — never a Postgres pool (PROJECT_SPEC §34.2)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

from app.config import normalize_supabase_url

logger = logging.getLogger("cuvoy.supabase")


def _eq_params(filters: dict[str, str] | None) -> dict[str, str]:
    if not filters:
        return {}
    return {key: f"eq.{value}" for key, value in filters.items()}


class SupabaseRest:
    def __init__(self, url: str, service_role_key: str, http: httpx.AsyncClient) -> None:
        self._base = normalize_supabase_url(url)
        self._key = service_role_key
        self._http = http

    def _headers(
        self,
        extra: dict[str, str] | None = None,
        *,
        user_token: str | None = None,
    ) -> dict[str, str]:
        headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {user_token or self._key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    async def ping(self) -> bool:
        if not self._base:
            return False
        try:
            response = await self._http.get(f"{self._base}/rest/v1/", headers=self._headers())
            return response.status_code < 500
        except httpx.HTTPError as exc:
            logger.warning("db_ping_failed", extra={"provider": "supabase", "error": str(exc)})
            return False

    async def insert(
        self,
        table: str,
        row: dict[str, Any],
        *,
        user_token: str | None = None,
    ) -> dict[str, Any] | None:
        """Best-effort persist. Missing tables must not break planning."""
        rows = await self._write(
            "POST",
            table,
            json=row,
            extra={"Prefer": "return=representation"},
            user_token=user_token,
        )
        if rows is None:
            return None
        return rows[0] if rows else dict(row)

    async def upsert(
        self,
        table: str,
        row: dict[str, Any],
        *,
        on_conflict: str = "id",
    ) -> dict[str, Any] | None:
        rows = await self._write(
            "POST",
            table,
            json=row,
            extra={"Prefer": "return=representation,resolution=merge-duplicates"},
            params={"on_conflict": on_conflict},
        )
        if rows is None:
            return None
        return rows[0] if rows else dict(row)

    async def patch(
        self,
        table: str,
        match: dict[str, str],
        row: dict[str, Any],
        *,
        user_token: str | None = None,
    ) -> bool:
        rows = await self._write(
            "PATCH",
            table,
            json=row,
            extra={"Prefer": "return=minimal"},
            params=_eq_params(match),
            user_token=user_token,
        )
        return rows is not None

    async def select(
        self,
        table: str,
        *,
        filters: dict[str, str] | None = None,
        order: str | None = None,
        limit: int | None = None,
        user_token: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = _eq_params(filters)
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = str(limit)
        try:
            response = await self._http.get(
                f"{self._base}/rest/v1/{table}",
                headers=self._headers(user_token=user_token),
                params=params,
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "supabase_select_failed",
                extra={"provider": "supabase", "table": table, "error": str(exc)},
            )
            return []
        if response.status_code >= 400:
            logger.warning(
                "supabase_select_failed",
                extra={
                    "provider": "supabase",
                    "table": table,
                    "status_code": response.status_code,
                },
            )
            return []
        payload = response.json()
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    async def delete(self, table: str, *, filters: dict[str, str]) -> int:
        try:
            response = await self._http.delete(
                f"{self._base}/rest/v1/{table}",
                headers=self._headers({"Prefer": "return=representation"}),
                params=_eq_params(filters),
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "supabase_delete_failed",
                extra={"provider": "supabase", "table": table, "error": str(exc)},
            )
            return 0
        if response.status_code >= 400:
            logger.warning(
                "supabase_delete_failed",
                extra={
                    "provider": "supabase",
                    "table": table,
                    "status_code": response.status_code,
                },
            )
            return 0
        payload = response.json()
        if isinstance(payload, list):
            return len(payload)
        return 0

    async def auth_user(self, access_token: str) -> dict[str, Any] | None:
        """Validate a Supabase Auth JWT via GET /auth/v1/user (PROJECT_SPEC §7.19)."""
        if not self._base or not access_token:
            return None
        try:
            response = await self._http.get(
                f"{self._base}/auth/v1/user",
                headers={
                    "apikey": self._key,
                    "Authorization": f"Bearer {access_token}",
                },
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "supabase_auth_failed",
                extra={"provider": "supabase", "error": str(exc)},
            )
            return None
        if response.status_code >= 400:
            return None
        payload = response.json()
        return payload if isinstance(payload, dict) and payload.get("id") else None

    async def delete_auth_user(self, user_id: str) -> bool:
        if not self._base or not user_id:
            return False
        try:
            UUID(user_id)
        except ValueError:
            return False
        try:
            response = await self._http.delete(
                f"{self._base}/auth/v1/admin/users/{user_id}",
                headers=self._headers(),
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "supabase_auth_delete_failed",
                extra={"provider": "supabase", "error": str(exc)},
            )
            return False
        return response.status_code < 400

    async def _write(
        self,
        method: str,
        table: str,
        *,
        json: dict[str, Any],
        extra: dict[str, str],
        params: dict[str, str] | None = None,
        user_token: str | None = None,
    ) -> list[dict[str, Any]] | None:
        try:
            response = await self._http.request(
                method,
                f"{self._base}/rest/v1/{table}",
                headers=self._headers(extra, user_token=user_token),
                params=params,
                json=json,
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "supabase_write_failed",
                extra={"provider": "supabase", "table": table, "error": str(exc)},
            )
            return None
        if response.status_code >= 400:
            logger.warning(
                "supabase_write_failed",
                extra={
                    "provider": "supabase",
                    "table": table,
                    "status_code": response.status_code,
                    "error": response.text[:400],
                },
            )
            return None
        if response.status_code == 204 or not response.content:
            return []
        payload = response.json()
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []


class NullSupabase:
    async def ping(self) -> bool:
        return False

    async def insert(
        self,
        table: str,
        row: dict[str, Any],
        *,
        user_token: str | None = None,
    ) -> dict[str, Any] | None:
        return None

    async def upsert(
        self,
        table: str,
        row: dict[str, Any],
        *,
        on_conflict: str = "id",
    ) -> dict[str, Any] | None:
        return None

    async def patch(
        self,
        table: str,
        match: dict[str, str],
        row: dict[str, Any],
        *,
        user_token: str | None = None,
    ) -> bool:
        return False

    async def select(
        self,
        table: str,
        *,
        filters: dict[str, str] | None = None,
        order: str | None = None,
        limit: int | None = None,
        user_token: str | None = None,
    ) -> list[dict[str, Any]]:
        return []

    async def delete(self, table: str, *, filters: dict[str, str]) -> int:
        return 0

    async def auth_user(self, access_token: str) -> dict[str, Any] | None:
        return None

    async def delete_auth_user(self, user_id: str) -> bool:
        return False
