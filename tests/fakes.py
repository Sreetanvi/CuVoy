"""In-memory Supabase stand-in for auth and persistence tests."""

from __future__ import annotations

from typing import Any
from uuid import uuid4


class MemorySupabase:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "users": [],
            "planning_jobs": [],
            "trips": [],
            "exports": [],
        }
        self.tokens: dict[str, dict[str, Any]] = {}
        self.deleted_auth: list[str] = []

    def add_user(
        self,
        user_id: str,
        *,
        email: str = "user@example.com",
        token: str = "test-token",
    ) -> str:
        self.tokens[token] = {"id": user_id, "email": email}
        return token

    def _rows(self, table: str) -> list[dict[str, Any]]:
        return self.tables.setdefault(table, [])

    def _matches(self, row: dict[str, Any], filters: dict[str, str] | None) -> bool:
        if not filters:
            return True
        return all(str(row.get(key)) == str(value) for key, value in filters.items())

    async def ping(self) -> bool:
        return True

    async def insert(
        self,
        table: str,
        row: dict[str, Any],
        *,
        user_token: str | None = None,  # noqa: ARG002
    ) -> dict[str, Any] | None:
        stored = dict(row)
        stored.setdefault("id", str(uuid4()))
        self._rows(table).append(stored)
        return dict(stored)

    async def upsert(
        self,
        table: str,
        row: dict[str, Any],
        *,
        on_conflict: str = "id",
    ) -> dict[str, Any] | None:
        key = str(row.get(on_conflict))
        rows = self._rows(table)
        for index, existing in enumerate(rows):
            if str(existing.get(on_conflict)) == key:
                merged = {**existing, **row}
                rows[index] = merged
                return dict(merged)
        return await self.insert(table, row)

    async def patch(
        self,
        table: str,
        match: dict[str, str],
        row: dict[str, Any],
        *,
        user_token: str | None = None,
    ) -> bool:
        found = False
        for existing in self._rows(table):
            if self._matches(existing, match):
                existing.update(row)
                found = True
        return found

    async def select(
        self,
        table: str,
        *,
        filters: dict[str, str] | None = None,
        order: str | None = None,
        limit: int | None = None,
        user_token: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = [dict(row) for row in self._rows(table) if self._matches(row, filters)]
        if order:
            field = order.split(".")[0]
            descending = order.endswith(".desc")
            rows.sort(key=lambda item: str(item.get(field) or ""), reverse=descending)
        if limit is not None:
            rows = rows[:limit]
        return rows

    async def delete(self, table: str, *, filters: dict[str, str]) -> int:
        rows = self._rows(table)
        kept: list[dict[str, Any]] = []
        removed = 0
        for row in rows:
            if self._matches(row, filters):
                removed += 1
            else:
                kept.append(row)
        self.tables[table] = kept
        return removed

    async def auth_user(self, access_token: str) -> dict[str, Any] | None:
        return self.tokens.get(access_token)

    async def delete_auth_user(self, user_id: str) -> bool:
        self.deleted_auth.append(user_id)
        stale = [token for token, payload in self.tokens.items() if payload.get("id") == user_id]
        for token in stale:
            del self.tokens[token]
        return True
