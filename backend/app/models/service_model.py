from datetime import datetime, timezone
from dataclasses import dataclass, field
import uuid

@dataclass(slots=True)
class ProviderServicesModel:
    provider_mobile: str
    services: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_document(self) -> dict:
        return {
            "provider_mobile": self.provider_mobile,
            "services": self.services,
            "created_at": self.created_at,
        }

@dataclass(slots=True)
class ServiceNodeModel:
    service_id: str
    provider_mobile: str
    role: str
    service_type: str
    title: str
    description: str
    location: dict
    pricing: dict
    capacity: dict
    features: dict
    images: dict
    availability: dict
    rating: float = 0.0
    total_reviews: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_document(self) -> dict:
        return {
            "service_id": self.service_id,
            "provider_mobile": self.provider_mobile,
            "role": self.role,
            "service_type": self.service_type,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "pricing": self.pricing,
            "capacity": self.capacity,
            "features": self.features,
            "images": self.images,
            "availability": self.availability,
            "rating": self.rating,
            "total_reviews": self.total_reviews,
            "created_at": self.created_at,
        }