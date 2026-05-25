import asyncio
import base64
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from supabase import Client, create_client

_SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
_SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
_BUCKET = "evidence-files"


def _get_client() -> Client:
    if not _SUPABASE_URL or not _SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in the environment."
        )
    return create_client(_SUPABASE_URL, _SUPABASE_SERVICE_KEY)


def generate_case_id() -> str:
    return f"SNT-{uuid.uuid4().hex[:8].upper()}"


# ── Sync helpers (called via asyncio.to_thread) ───────────────────────────────

def _upload_file_sync(file_path: str, file_bytes: bytes) -> None:
    client = _get_client()
    client.storage.from_(_BUCKET).upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": "application/octet-stream", "upsert": "true"},
    )


def _insert_case_sync(row: dict) -> None:
    _get_client().table("cases").insert(row).execute()


def _download_file_sync(file_path: str) -> bytes:
    return _get_client().storage.from_(_BUCKET).download(file_path)


def _fetch_case_sync(case_id: str) -> Optional[dict]:
    result = (
        _get_client()
        .table("cases")
        .select("*")
        .eq("case_id", case_id)
        .maybe_single()
        .execute()
    )
    return result.data


# ── Public async interface ────────────────────────────────────────────────────

async def store_evidence(
    *,
    case_id: str,
    sha256_hash: str,
    captured_at: datetime,
    file_bytes: bytes,
    file_extension: str,
    source_url: Optional[str],
    filename: Optional[str],
    ots_status: str,
    ots_receipt: Optional[bytes],
    deepfake_result: dict,
) -> None:
    file_path = f"{case_id}/content{file_extension}"
    ots_b64 = base64.b64encode(ots_receipt).decode() if ots_receipt else None

    row = {
        "case_id": case_id,
        "sha256_hash": sha256_hash,
        "captured_at": captured_at.isoformat(),
        "source_url": source_url,
        "filename": filename,
        "file_path": file_path,
        "ots_status": ots_status,
        "ots_receipt_b64": ots_b64,
        "df_status": deepfake_result.get("status"),
        "df_is_deepfake": deepfake_result.get("is_deepfake"),
        "df_confidence": deepfake_result.get("confidence"),
        "df_reason": deepfake_result.get("reason"),
    }

    await asyncio.gather(
        asyncio.to_thread(_upload_file_sync, file_path, file_bytes),
        asyncio.to_thread(_insert_case_sync, row),
    )


async def get_case(case_id: str) -> Optional[dict]:
    return await asyncio.to_thread(_fetch_case_sync, case_id)


async def download_evidence_file(file_path: str) -> bytes:
    return await asyncio.to_thread(_download_file_sync, file_path)
