import asyncio
import mimetypes
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import Response

from models import DeepfakeResult, EvidenceResponse
from services.deepfake import analyze_deepfake
from services.hasher import compute_sha256
from services.storage import download_evidence_file, generate_case_id, get_case, store_evidence
from services.timestamp import submit_to_opentimestamps

router = APIRouter(prefix="/evidence", tags=["evidence"])

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB

_LOGIN_WALL_PHRASES = [
    "log in to instagram",
    "login to instagram",
    "sign in to instagram",
    "log in to facebook",
    "log in to twitter",
    "sign in to x",
    "log in to tiktok",
    "sign in to continue",
    "you must log in",
    "create an account",
    "join instagram",
    "accounts/login",
    "login?next=",
    "signin?redirect",
]

_LOGIN_WALL_URL_PATTERNS = [
    "/accounts/login",
    "/login?",
    "/signin?",
    "/sign-in?",
    "/auth/login",
]


def _is_login_wall(final_url: str, html: bytes) -> bool:
    url_lower = final_url.lower()
    if any(p in url_lower for p in _LOGIN_WALL_URL_PATTERNS):
        return True
    try:
        text = html[:8000].decode("utf-8", errors="ignore").lower()
        if sum(1 for p in _LOGIN_WALL_PHRASES if p in text) >= 2:
            return True
    except Exception:
        pass
    return False


def _extension_from_content_type(content_type: str, filename: str) -> str:
    ext = os.path.splitext(filename)[1]
    if ext:
        return ext
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
    return guessed or ".bin"


@router.post("/capture-url", response_model=EvidenceResponse)
async def capture_url(url: str = Form(...)):
    """
    Download the content at `url`, compute its SHA-256, submit to
    OpenTimestamps, optionally run deepfake detection, persist to Supabase,
    and return an EvidenceResponse.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; Sentinel-Evidence-Capture/1.0; "
            "+https://sentinel-saver.vercel.app)"
        )
    }
    try:
        async with httpx.AsyncClient(
            timeout=30.0, follow_redirects=True, headers=headers
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Target URL returned HTTP {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=422, detail=f"Could not reach URL: {exc}"
        )

    content = resp.content
    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=413, detail="URL content exceeds the 10 MB limit"
        )

    content_type: str = resp.headers.get("content-type", "application/octet-stream")

    if "text/html" in content_type and _is_login_wall(str(resp.url), content):
        raise HTTPException(
            status_code=422,
            detail=(
                "This platform requires login to view content — Sentinel cannot "
                "capture it directly. Take a screenshot while logged in and use "
                "the File Upload tab instead."
            ),
        )
    case_id = generate_case_id()
    sha256_hash = compute_sha256(content)
    captured_at = datetime.now(timezone.utc)

    ots_task = submit_to_opentimestamps(sha256_hash)
    df_task = analyze_deepfake(content, content_type.split(";")[0].strip(), "capture")

    (ots_status, ots_receipt), deepfake_result = await asyncio.gather(
        ots_task, df_task
    )

    ext = _extension_from_content_type(content_type, url)
    await store_evidence(
        case_id=case_id,
        sha256_hash=sha256_hash,
        captured_at=captured_at,
        file_bytes=content,
        file_extension=ext,
        source_url=url,
        filename=None,
        ots_status=ots_status,
        ots_receipt=ots_receipt,
        deepfake_result=deepfake_result,
    )

    return EvidenceResponse(
        case_id=case_id,
        sha256_hash=sha256_hash,
        captured_at=captured_at.isoformat(),
        source_url=url,
        ots_status=ots_status,
        deepfake_result=DeepfakeResult(**deepfake_result),
    )


@router.post("/upload", response_model=EvidenceResponse)
async def upload_file(file: UploadFile):
    """
    Accept an uploaded file, compute its SHA-256, submit to
    OpenTimestamps, optionally run deepfake detection, persist, and respond.
    """
    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=413, detail="File exceeds the 10 MB limit"
        )
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    case_id = generate_case_id()
    sha256_hash = compute_sha256(content)
    captured_at = datetime.now(timezone.utc)

    ots_task = submit_to_opentimestamps(sha256_hash)
    df_task = analyze_deepfake(content, content_type, filename)

    (ots_status, ots_receipt), deepfake_result = await asyncio.gather(
        ots_task, df_task
    )

    ext = _extension_from_content_type(content_type, filename)
    await store_evidence(
        case_id=case_id,
        sha256_hash=sha256_hash,
        captured_at=captured_at,
        file_bytes=content,
        file_extension=ext,
        source_url=None,
        filename=filename,
        ots_status=ots_status,
        ots_receipt=ots_receipt,
        deepfake_result=deepfake_result,
    )

    return EvidenceResponse(
        case_id=case_id,
        sha256_hash=sha256_hash,
        captured_at=captured_at.isoformat(),
        filename=filename,
        ots_status=ots_status,
        deepfake_result=DeepfakeResult(**deepfake_result),
    )


@router.get("/{case_id}/file")
async def download_file(case_id: str):
    """Download the original captured file for independent hash verification."""
    row = await get_case(case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    file_path: str = row.get("file_path", "")
    if not file_path:
        raise HTTPException(status_code=404, detail="No file stored for this case")

    file_bytes = await download_evidence_file(file_path)
    ext = os.path.splitext(file_path)[1]
    content_type = mimetypes.types_map.get(ext, "application/octet-stream")
    filename = row.get("filename") or f"evidence-{case_id}{ext}"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{case_id}", response_model=EvidenceResponse)
async def get_evidence(case_id: str):
    """Retrieve a previously captured evidence record by case ID."""
    row = await get_case(case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    df_result = None
    if row.get("df_status"):
        df_result = DeepfakeResult(
            status=row["df_status"],
            is_deepfake=row.get("df_is_deepfake"),
            confidence=row.get("df_confidence"),
            reason=row.get("df_reason"),
        )

    return EvidenceResponse(
        case_id=row["case_id"],
        sha256_hash=row["sha256_hash"],
        captured_at=row["captured_at"],
        source_url=row.get("source_url"),
        filename=row.get("filename"),
        ots_status=row.get("ots_status"),
        deepfake_result=df_result,
    )
