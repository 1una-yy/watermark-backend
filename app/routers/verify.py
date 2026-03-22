import base64

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import EmbedTask, Image, User, VerifyLog
from app.schemas import VerifyLogRead, VerifyRequest
from app.services import storage, watermark_api

router = APIRouter(prefix="/verify", tags=["verify"])


async def _get_image_bytes(
    body: VerifyRequest,
    current_user: User,
    db: AsyncSession,
) -> tuple[bytes, str | None]:
    """Resolve image bytes from DB image_id or external URL."""
    if body.image_id:
        img_result = await db.execute(
            select(Image).where(Image.id == body.image_id, Image.user_id == current_user.id)
        )
        image = img_result.scalar_one_or_none()
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found")
        url = image.blob_url
    elif body.image_url:
        url = body.image_url
    else:
        raise HTTPException(status_code=422, detail="Provide either image_id or image_url")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    return resp.content, url


@router.post("/", response_model=VerifyLogRead, status_code=status.HTTP_201_CREATED)
async def run_verify(
    body: VerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_bytes, image_url = await _get_image_bytes(body, current_user, db)

    verify_result = await watermark_api.verify(
        image_bytes=image_bytes,
        metadata_json=body.metadata_json,
    )

    # Upload EditGuard mask to Vercel Blob
    mask_url: str | None = None
    if verify_result.get("editguard_mask_base64"):
        mask_data = base64.b64decode(verify_result["editguard_mask_base64"])
        blob = await storage.upload_image(
            data=mask_data,
            filename="verify_mask.png",
            content_type="image/png",
            folder=f"verify/{current_user.id}",
        )
        mask_url = blob["url"]

    summary = verify_result.get("summary", {})
    log = VerifyLog(
        user_id=current_user.id,
        embed_task_id=body.embed_task_id,
        image_url=image_url,
        stegastamp_found_codes=verify_result.get("stegastamp_found_codes"),
        editguard_recovered_bits=verify_result.get("editguard_recovered_bits"),
        editguard_accuracy=verify_result.get("editguard_accuracy"),
        mask_url=mask_url,
        summary=summary,
        overall_pass=summary.get("overall_pass"),
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


@router.get("/", response_model=list[VerifyLogRead])
async def list_verify_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VerifyLog)
        .where(VerifyLog.user_id == current_user.id)
        .order_by(VerifyLog.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{log_id}", response_model=VerifyLogRead)
async def get_verify_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VerifyLog).where(VerifyLog.id == log_id, VerifyLog.user_id == current_user.id)
    )
    log = result.scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=404, detail="Verify log not found")
    return log
