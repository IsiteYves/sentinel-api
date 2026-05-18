import binascii
import httpx
from typing import Optional, Tuple

_OTS_POOLS = [
    "https://a.pool.opentimestamps.org/digest",
    "https://b.pool.opentimestamps.org/digest",
    "https://c.pool.opentimestamps.org/digest",
]


async def submit_to_opentimestamps(sha256_hex: str) -> Tuple[str, Optional[bytes]]:
    """
    Submit a SHA-256 hash to the OpenTimestamps public calendar servers.

    Returns (status, ots_receipt_bytes).
    The receipt is stored so it can be verified against the Bitcoin blockchain
    once a block confirms (usually ~60 minutes after submission).
    """
    hash_bytes = binascii.unhexlify(sha256_hex)

    async with httpx.AsyncClient(timeout=15.0) as client:
        for pool_url in _OTS_POOLS:
            try:
                resp = await client.post(
                    pool_url,
                    content=hash_bytes,
                    headers={"Content-Type": "application/octet-stream"},
                )
                if resp.status_code == 200:
                    return "pending_bitcoin_confirmation", resp.content
            except httpx.RequestError:
                continue

    return "timestamp_unavailable", None
