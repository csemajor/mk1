from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    service_id: str = Field(..., min_length=1)
    booking_id: str = Field(..., min_length=1)
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(default="", max_length=2000)
    images: list[str] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    id: str
    user_id: str
    user_mobile: str
    service_id: str
    booking_id: str
    rating: int
    comment: str
    images: list[str]
    created_at: datetime


class ReviewCreateResponse(BaseModel):
    success: bool
    data: ReviewResponse


class ReviewListResponse(BaseModel):
    success: bool
    data: list[ReviewResponse]
