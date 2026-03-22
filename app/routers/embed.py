import base64

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import AsyncSessionLocal, get_db
from app.models import EmbedTask, Image, User
from app.schemas import EmbedTaskCreate, EmbedTaskRead
from app.services import storage, watermark_api

router = APIRouter(prefix="/embed", tags=["embed"])


async def _run_embed(task_id: str, image_bytes: bytes) -> None:
    """Background job: call partner API, upload results, update DB."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(EmbedTask).where(EmbedTask.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return

        try:
            task.status = "processing"
            await db.commit()

            embed_result = await watermark_api.embed(
                image_bytes=image_bytes,
                editguard_bits=task.editguard_bits,
                stegastamp_secret=task.stegastamp_secret,
            )

            async def _upload_b64(b64_str: str, label: str) -> str:
                data = base64.b64decode(b64_str)
                blob = await storage.upload_image(
                    data=data,
                    filename=f"{task_id}_{label}.png",
                    content_type="image/png",
                    folder=f"tasks/{task_id}",
                )
                return blob["url"]

            task.metadata_json = embed_result["metadata_json"]
            task.result_image_url = await _upload_b64(embed_result["final_image_base64"], "final")
            task.stegastamp_image_url = await _upload_b64(embed_result["stegastamp_image_base64"], "stegastamp")
            task.residual_image_url = await _upload_b64(embed_result["stegastamp_residual_base64"], "residual")
            task.status = "done"

        except (httpx.HTTPError, Exception) as exc:
            task.status = "failed"
            task.error_message = str(exc)

        await db.commit()


@router.post("/", response_model=EmbedTaskRead, status_code=status.HTTP_202_ACCEPTED)
async def create_embed_task(
    body: EmbedTaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify image belongs to user
    img_result = await db.execute(
        select(Image).where(Image.id == body.image_id, Image.user_id == current_user.id)
    )
    image = img_result.scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # Fetch image bytes from Vercel Blob
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(image.blob_url)
        resp.raise_for_status()
        image_bytes = resp.content

    task = EmbedTask(
        user_id=current_user.id,
        source_image_id=image.id,
        editguard_bits=body.editguard_bits,
        stegastamp_secret=body.stegastamp_secret,
        status="pending",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    background_tasks.add_task(_run_embed, task.id, image_bytes)
    return task


@router.get("/", response_model=list[EmbedTaskRead])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmbedTask)
        .where(EmbedTask.user_id == current_user.id)
        .order_by(EmbedTask.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=EmbedTaskRead)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmbedTask).where(EmbedTask.id == task_id, EmbedTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
