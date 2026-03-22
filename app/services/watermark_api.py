"""
Async client wrapping the Dual-WaterMark FastAPI at api.watermark.nyanfox.com
"""

import base64

import httpx

from app.config import settings

_BASE = settings.WATERMARK_API_BASE_URL.rstrip("/")
_TIMEOUT = settings.WATERMARK_API_TIMEOUT


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


async def health_check() -> bool:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_BASE}/health")
        return resp.status_code == 200 and resp.json().get("ok") is True


async def random_bits() -> str:
    """Return a fresh 64-bit random bitstring from the partner API."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_BASE}/random-bits")
        resp.raise_for_status()
        return resp.json()["bits"]


async def embed(
    image_bytes: bytes,
    editguard_bits: str,
    stegastamp_secret: str,
) -> dict:
    """
    Call POST /embed.

    Returns:
        metadata_json          str
        stegastamp_image_base64 str (base64 PNG)
        final_image_base64      str (base64 PNG)
        stegastamp_residual_base64 str (base64 PNG)
    """
    payload = {
        "image_base64": _b64(image_bytes),
        "editguard_bits": editguard_bits,
        "stegastamp_secret": stegastamp_secret,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{_BASE}/embed", json=payload)
        resp.raise_for_status()
        return resp.json()


async def inpaint(
    image_bytes: bytes,
    mask_bytes: bytes,
    prompt: str = "repair tampered region",
) -> dict:
    """
    Call POST /inpaint.

    Returns:
        inpainted_image_base64  str (base64 PNG)
    """
    payload = {
        "image_base64": _b64(image_bytes),
        "mask_base64": _b64(mask_bytes),
        "prompt": prompt,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{_BASE}/inpaint", json=payload)
        resp.raise_for_status()
        return resp.json()


async def verify(
    image_bytes: bytes,
    metadata_json: str,
) -> dict:
    """
    Call POST /verify.

    Returns:
        stegastamp_found_codes     list
        editguard_recovered_bits   str
        editguard_accuracy         str
        editguard_mask_base64      str (base64 PNG)
        summary                    dict
            - editguard_intact     bool
            - copyright_match      bool
            - fingerprint_match    bool
            - overall_pass         bool
    """
    payload = {
        "image_base64": _b64(image_bytes),
        "metadata_json": metadata_json,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{_BASE}/verify", json=payload)
        resp.raise_for_status()
        return resp.json()
