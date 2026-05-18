import os
import httpx
from typing import Optional

_HIVE_API_KEY: str = os.getenv("HIVE_API_KEY", "")
_HIVE_ENDPOINT = "https://api.thehive.ai/api/v2/task/sync"

_ANALYZABLE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


async def analyze_deepfake(
    file_bytes: bytes,
    content_type: str,
    filename: str,
) -> dict:
    """
    Send media to Hive AI for deepfake detection.

    Returns a dict matching the DeepfakeResult schema:
      status: "analyzed" | "skipped" | "error"
      is_deepfake: bool or None
      confidence: float (0-100) or None
      reason: str or None
    """
    if not _HIVE_API_KEY:
        return {
            "status": "skipped",
            "is_deepfake": None,
            "confidence": None,
            "reason": "Analysis not configured",
        }

    if content_type not in _ANALYZABLE_TYPES:
        return {
            "status": "skipped",
            "is_deepfake": None,
            "confidence": None,
            "reason": "File type not supported for deepfake analysis",
        }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                _HIVE_ENDPOINT,
                headers={"Authorization": f"Token {_HIVE_API_KEY}"},
                files={"media": (filename, file_bytes, content_type)},
            )
            resp.raise_for_status()
            data = resp.json()

        classes: list = (
            data.get("status", [{}])[0]
            .get("response", {})
            .get("output", [{}])[0]
            .get("classes", [])
        )
        # Hive returns {"class": "yes"/"no", "score": float}
        # "yes" == this IS a deepfake
        deepfake_score: float = next(
            (c["score"] for c in classes if c.get("class") == "yes"), 0.0
        )

        return {
            "status": "analyzed",
            "is_deepfake": deepfake_score > 0.5,
            "confidence": round(deepfake_score * 100, 1),
            "reason": None,
        }

    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "is_deepfake": None,
            "confidence": None,
            "reason": f"Hive API error {exc.response.status_code}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "is_deepfake": None,
            "confidence": None,
            "reason": str(exc),
        }
