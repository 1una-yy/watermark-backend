import hashlib

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import Image, User
from app.schemas import ImageRead
from app.services.storage import upload_image

router = APIRouter(prefix="/images", tags=["images"])

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, WEBP are accepted")

    data = await file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")

    sha256 = hashlib.sha256(data).hexdigest()
    blob_result = await upload_image(
        data=data,
        filename=file.filename or "upload.png",
        content_type=file.content_type,
        folder=f"users/{current_user.id}",
    )

    image = Image(
        user_id=current_user.id,
        original_filename=file.filename or "upload.png",
        blob_url=blob_result["url"],
        blob_pathname=blob_result["pathname"],
        file_size=len(data),
        mime_type=file.content_type,
        sha256=sha256,
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)
    return image


@router.get("/", response_model=list[ImageRead])
async def list_images(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Image).where(Image.user_id == current_user.id).order_by(Image.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{image_id}", response_model=ImageRead)
async def get_image(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.user_id == current_user.id)
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return image
