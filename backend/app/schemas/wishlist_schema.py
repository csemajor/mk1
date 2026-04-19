from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WishlistMutationRequest(BaseModel):
    service_id: str = Field(..., min_length=1)

    @field_validator("service_id")
    @classmethod
    def normalize_service_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("service_id is required")
        return cleaned


class WishlistItemResponse(BaseModel):
    service_id: str
    added_at: datetime | None = None


class WishlistResponse(BaseModel):
    success: bool = True
    user_mobile: str = ""
    wishlist: list[WishlistItemResponse] = Field(default_factory=list)
