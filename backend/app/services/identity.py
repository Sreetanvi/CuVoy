"""Anonymous vs account identity for plan credits (PROJECT_SPEC §7.3)."""

from __future__ import annotations

import hashlib

from fastapi import Request


def hash_identity(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def credit_identity(*, user_id: str | None, ip: str, fingerprint: str | None) -> str:
    if user_id:
        return f"user:{user_id}"
    material = f"{ip}:{fingerprint or ''}"
    return f"anon:{hash_identity(material)}"


def identity_from_request(request: Request, user_id: str | None = None) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not ip and request.client:
        ip = request.client.host
    fingerprint = request.headers.get("x-cuvoy-fingerprint")
    return credit_identity(user_id=user_id, ip=ip or "unknown", fingerprint=fingerprint)
