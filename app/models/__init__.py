import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer,
    String, Text, func,
)
from sqlalchemy.dialects.mysql import CHAR, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────
# User
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    images: Mapped[list["Image"]] = relationship("Image", back_populates="user")
    embed_tasks: Mapped[list["EmbedTask"]] = relationship("EmbedTask", back_populates="user")
    verify_logs: Mapped[list["VerifyLog"]] = relationship("VerifyLog", back_populates="user")


# ─────────────────────────────────────────────
# Image  (original uploaded files)
# ─────────────────────────────────────────────
class Image(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    blob_pathname: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="images")
    embed_tasks: Mapped[list["EmbedTask"]] = relationship("EmbedTask", back_populates="source_image")


# ─────────────────────────────────────────────
# EmbedTask  (watermark embedding jobs)
# ─────────────────────────────────────────────
class EmbedTask(Base):
    __tablename__ = "embed_tasks"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"))
    source_image_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("images.id", ondelete="RESTRICT"))

    editguard_bits: Mapped[str] = mapped_column(String(64), nullable=False)
    stegastamp_secret: Mapped[str] = mapped_column(String(7), nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "done", "failed"),
        default="pending",
        nullable=False,
    )

    # Returned by /embed
    metadata_json: Mapped[str | None] = mapped_column(Text)
    result_image_url: Mapped[str | None] = mapped_column(String(1024))
    stegastamp_image_url: Mapped[str | None] = mapped_column(String(1024))
    residual_image_url: Mapped[str | None] = mapped_column(String(1024))
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="embed_tasks")
    source_image: Mapped["Image"] = relationship("Image", back_populates="embed_tasks")
    verify_logs: Mapped[list["VerifyLog"]] = relationship("VerifyLog", back_populates="embed_task")


# ─────────────────────────────────────────────
# VerifyLog  (verification history)
# ─────────────────────────────────────────────
class VerifyLog(Base):
    __tablename__ = "verify_logs"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"))
    embed_task_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("embed_tasks.id", ondelete="SET NULL"), nullable=True
    )

    image_url: Mapped[str | None] = mapped_column(String(1024))
    stegastamp_found_codes: Mapped[dict | None] = mapped_column(JSON)
    editguard_recovered_bits: Mapped[str | None] = mapped_column(String(64))
    editguard_accuracy: Mapped[str | None] = mapped_column(String(20))
    mask_url: Mapped[str | None] = mapped_column(String(1024))
    summary: Mapped[dict | None] = mapped_column(JSON)
    overall_pass: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="verify_logs")
    embed_task: Mapped["EmbedTask | None"] = relationship("EmbedTask", back_populates="verify_logs")
