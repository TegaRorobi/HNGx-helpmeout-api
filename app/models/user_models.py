""" User models. """
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """The user model"""

    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)
    username: str = Column(
        String, index=True, unique=True, nullable=False, default=None
    )
    email: Optional[str] = Column(String, nullable=True, default=None)
    hashed_password: str = Column(String, nullable=False)
    created_date: DateTime = Column(DateTime, server_default=func.now())
    updated_date: Optional[DateTime] = Column(DateTime, onupdate=func.now())
    is_deleted: bool = Column(Boolean, default=False)

    # Add a unique constraint on 'username' and 'hashed_password' combination
    __table_args__ = (
        UniqueConstraint("username", "hashed_password", name="unique_user"),
    )


class UserRequest(BaseModel):
    """The user request model"""

    username: str
    email: Optional[str] = None


class UserAuthentication(UserRequest):
    """The user authentication model"""

    password: str


class UpdateUsername(BaseModel):
    new_username: str


class UserResponse(BaseModel):
    """The user response model"""

    message: str
    status_code: int
    username: Optional[str] = None


class LogoutResponse(BaseModel):
    """The logout response model"""

    message: str
    status_code: int


class OtpResponse(BaseModel):
    """The OTP response model"""
    status_code: int
    message: str
    username: Optional[str] = None
    verification_code: Optional[int] = None
