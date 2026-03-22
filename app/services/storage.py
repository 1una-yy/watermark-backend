"""
Vercel Blob REST API wrapper.
Docs: https://vercel.com/docs/storage/vercel-blob/using-blob-sdk#upload-a-blob
"""

import mimetypes
import uuid

import httpx

from app.config import settings

BLOB_API_VERSION = "7"
BLOB_BASE_URL = "https://blob.vercel-storage.com"


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.BLOB_READ_WRITE_TOKEN}",
        "x-api-version": BLOB_API_VERSION,
    }


async def upload_image(
    data: bytes,
    filename: str,
    content_type: str | None = None,
    folder: str = "images",
) -> dict:
    """
    Upload raw bytes to Vercel Blob.

    Returns dict with keys: url, downloadUrl, pathname, contentType
    """
    if content_type is None:
        content_type = mimetypes.guess_type(filename)[0] or "image/png"

    # Build a unique pathname to avoid collisions
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "png"
    unique_name = f"{folder}/{uuid.uuid4().hex}.{ext}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.put(
            f"{BLOB_BASE_URL}/{unique_name}",
            content=data,
            headers={
                **_auth_headers(),
                "Content-Type": content_type,
                "x-content-type": content_type,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def delete_blob(url: str) -> None:
    """Delete a blob by its public URL."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(
            f"{BLOB_BASE_URL}/delete",
            json={"urls": [url]},
            headers=_auth_headers(),
        )
        resp.raise_for_status()
