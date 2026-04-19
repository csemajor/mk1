from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class BookingSlot(str, Enum):
    MORNING = "morning"
    EVENING = "evening"


class BookingCreateRequest(BaseModel):
    service_id: str = Field(..., min_length=1)
    date: date
    slot: str = Field(..., min_length=1)
    advance_paid: float = Field(default=0.0, ge=0)


class BookingResponse(BaseModel):
    id: str
    user_id: str
    service_id: str
    provider_mobile: str
    user_mobile: str
    user_location: dict
    date: date
    slot: str
    total_price: float
    advance_paid: float
    status: str
    created_at: datetime
    cancelled_at: datetime | None = None


class BookingCreateResponse(BaseModel):
    success: bool
    data: BookingResponse


class BookingListResponse(BaseModel):
    success: bool
    data: list[BookingResponse]


class MyBookingItem(BaseModel):
    booking_id: str
    service_id: str
    service_name: str
    date: str
    slot: str
    price: float
    advance_paid: float
    provider_contact: str
    status: str
    is_reviewed: bool = False

class MyBookingListResponse(BaseModel):
    success: bool
    data: list[MyBookingItem]
