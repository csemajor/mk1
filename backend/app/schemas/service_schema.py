from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing import Optional

class LocationSchema(BaseModel):
    placeName: str = Field(default="")
    address: str = Field(default="")
    lat: float = Field(default=0.0)
    lng: float = Field(default=0.0)
    text: str = Field(default="")
    description: str = Field(default="")

class PricingSchema(BaseModel):
    amount: float = Field(..., ge=0)
    price_type: str = Field(..., min_length=1)
    pricing_description: str = Field(default="")
    advance_percentage: float = Field(default=0.0, ge=0, le=50)
    advance_amount: float = Field(default=0.0, ge=0)

    @model_validator(mode='after')
    def auto_calculate_advance(self):
        # Always enforce correct math over what UI sends safely
        self.advance_amount = float((self.amount * self.advance_percentage) / 100)
        return self

class CapacitySchema(BaseModel):
    min: int = Field(default=0, ge=0)
    max: int = Field(default=0, ge=0)

class ImagesSchema(BaseModel):
    cover_image_url: str = Field(..., min_length=1)
    gallery_urls: list[str] = Field(default_factory=list)

class AvailabilitySchema(BaseModel):
    dates: list[str] = Field(..., min_length=1)
    time_slot_type: str = Field(..., min_length=1)
    start_time: str = ""
    end_time: str = ""

    @model_validator(mode='after')
    def validate_times(self):
        txt = self.time_slot_type.lower()
        if txt != "full day":
            if not self.start_time or not self.end_time:
                raise ValueError("start_time and end_time are required unless time_slot_type is 'Full Day'")
        else:
            self.start_time = ""
            self.end_time = ""
        return self


class FeaturesSchema(BaseModel):
    predefined: list[str] = Field(default_factory=list, max_length=20)
    custom: list[str] = Field(default_factory=list, max_length=20)

    @staticmethod
    def _normalize(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            value = str(item).strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(value)
        return out

    @model_validator(mode='after')
    def normalize_lists(self):
        self.predefined = self._normalize(self.predefined)
        self.custom = self._normalize(self.custom)

        # Keep custom clean if it duplicates any predefined feature.
        predefined_keys = {value.casefold() for value in self.predefined}
        self.custom = [value for value in self.custom if value.casefold() not in predefined_keys]
        return self

class ServiceCreate(BaseModel):
    provider_mobile: str = Field(..., min_length=10)
    role: str = Field(...)
    service_type: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = Field(default="")
    location: LocationSchema
    pricing: PricingSchema
    capacity: CapacitySchema
    features: FeaturesSchema = Field(default_factory=FeaturesSchema)
    images: ImagesSchema
    availability: AvailabilitySchema
    rating: float = 0.0
    total_reviews: int = 0

class ServiceResponse(BaseModel):
    id: str = Field(alias="service_id")
    provider_mobile: str
    role: str
    service_type: str
    title: str
    description: str
    location: dict
    pricing: dict
    capacity: dict
    features: FeaturesSchema
    images: dict
    availability: dict
    rating: float
    total_reviews: int
    created_at: Optional[datetime] = None

    class Config:
        populate_by_name = True

class ServiceListResponse(BaseModel):
    success: bool
    count: int
    data: list[ServiceResponse]

class UploadImageResponse(BaseModel):
    success: bool
    url: str