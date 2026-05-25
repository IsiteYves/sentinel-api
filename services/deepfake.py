import base64
import os

import httpx

_HIVE_SECRET_KEY: str = os.getenv("HIVE_API_KEY", "")
_HIVE_ENDPOINT = "https://api.thehive.ai/api/v3/chat/completions"

_ANALYZABLE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

_PROMPT = (
    "Analyze this image carefully for signs of deepfake or AI manipulation. "
    "Look for unnatural facial features, inconsistent lighting, blurred edges, "
    "artifacts around hair or teeth, or any indication the image is synthetically "
    "generated or digitally altered to misrepresent reality. "
    "Respond with: is_deepfake (true if manipulated/AI-generated, false if authentic), "
    "confidence (integer 0-100), and reason (one sentence explanation)."
)

_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "deepfake_analysis",
        "schema": {
            "type": "object",
            "required": ["is_deepfake", "confidence", "reason"],
            "properties": {
                "is_deepfake": {"type": "boolean"},
                "confidence": {"type": "number"},
                "reason": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "strict": True,
    },
}


async def analyze_deepfake(
    file_bytes: bytes,
    content_type: str,
    filename: str,
) -> dict:
    """
    Send media to Hive VLM (V3) for deepfake / AI-manipulation detection.

    Returns a dict matching the DeepfakeResult schema:
      status: "analyzed" | "skipped" | "error"
      is_deepfake: bool or None
      confidence: float (0-100) or None
      reason: str or None
    """
    if not _HIVE_SECRET_KEY:
        return {
            "status": "skipped",
            "is_deepfake": None,
            "confidence": None,
            "reason": "Analysis not configured",
        }

    mime = content_type.split(";")[0].strip()
    if mime not in _ANALYZABLE_TYPES:
        return {
            "status": "skipped",
            "is_deepfake": None,
            "confidence": None,
            "reason": "File type not supported for deepfake analysis",
        }

    b64 = base64.b64encode(file_bytes).decode()
    data_url = f"data:{mime};base64,{b64}"

    payload = {
        "model": "hive/vision-language-model",
        "max_tokens": 100,
        "temperature": 0,
        "response_format": _RESPONSE_SCHEMA,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                _HIVE_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {_HIVE_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        import json
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)

        return {
            "status": "analyzed",
            "is_deepfake": bool(result["is_deepfake"]),
            "confidence": round(float(result["confidence"]), 1),
            "reason": result.get("reason"),
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
