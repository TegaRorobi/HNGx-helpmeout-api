""" The video models """""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Enum, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Video(Base):
    """ The video model """
    __tablename__ = "videos"

    id: str = Column(String, primary_key=True, unique=True, nullable=False)
    username: str = Column(
        String,
        ForeignKey("users.username", ondelete="CASCADE"),
        nullable=False,
    )
    title: str = Column(String, nullable=False)
    created_date: datetime = Column(DateTime, default=datetime.utcnow)
    original_location: Optional[str] = Column(String, nullable=True)
    compressed_location: Optional[str] = Column(String, nullable=True)
    thumbnail_location: Optional[str] = Column(String, nullable=True)
    transcript_location: Optional[str] = Column(String, nullable=True)
    status: str = Column(
        Enum(
            "processing",
            "completed",
            "failed",
            name="processing_status",
        ),
        default="processing",
    )
    is_public: bool = Column(Boolean, default=True)
    pa_expiry_date: Optional[datetime] = Column(DateTime, nullable=True)

    user = relationship("User", backref="videos")


class VideoBlob(BaseModel):
    """ The video blob model """
    username: str
    video_id: str
    blob_index: int
    blob_object: bytes
    is_last: bool
