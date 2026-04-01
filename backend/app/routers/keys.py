"""API Keys management routes."""
import uuid
import hashlib
import json
import secrets
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/keys", tags=["keys"])


class CreateKeyRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    permissions: List[str]


def generate_api_key() -> str:
    return f"ah_{secrets.token_hex(24)}"


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


@router.get("")
async def list_keys(request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, description, key_prefix, permissions, created_at, last_used_at FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
            (user["sub"],),
        ).fetchall()
        return [
            {**dict(r), "permissions": json.loads(r["permissions"])}
            for r in rows
        ]


@router.post("")
async def create_key(body: CreateKeyRequest, request: Request):
    user = get_current_user(request)
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Key name is required")
    if not body.permissions:
        raise HTTPException(status_code=400, detail="At least one permission is required")

    valid_permissions = {"read", "write", "delete", "admin"}
    for p in body.permissions:
        if p not in valid_permissions:
            raise HTTPException(status_code=400, detail=f"Invalid permission: {p}")

    raw_key = generate_api_key()
    key_id = f"key_{uuid.uuid4().hex[:12]}"

    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_keys (id, user_id, name, description, key_hash, key_prefix, permissions) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (key_id, user["sub"], body.name.strip(), body.description or "", hash_key(raw_key), raw_key[:11], json.dumps(body.permissions)),
        )

    return {
        "id": key_id,
        "name": body.name.strip(),
        "key": raw_key,
        "key_prefix": raw_key[:11],
        "permissions": body.permissions,
    }


@router.delete("/{key_id}")
async def delete_key(key_id: str, request: Request):
    user = get_current_user(request)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM api_keys WHERE id = ? AND user_id = ?",
            (key_id, user["sub"]),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Key not found")
        conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    return {"ok": True}
