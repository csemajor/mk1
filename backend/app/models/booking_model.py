from dataclasses import dataclass, field
from datetime import datetime, timezone

from bson import ObjectId


@dataclass(slots=True)
class BookingModel:
    user_id: str
    service_id: ObjectId
    provider_mobile: str
    user_mobile: str
    user_location: dict
    date: str
    slot: str
    total_price: float
    advance_paid: float = 0.0
    status: str = "confirmed"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cancelled_at: datetime | None = None

    def to_document(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "service_id": self.service_id,
            "provider_mobile": self.provider_mobile,
            "user_mobile": self.user_mobile,
            "user_location": self.user_location,
            "date": self.date,
            "slot": self.slot,
            "total_price": self.total_price,
            "advance_paid": self.advance_paid,
            "status": self.status,
            "created_at": self.created_at,
            "cancelled_at": self.cancelled_at,
        }
