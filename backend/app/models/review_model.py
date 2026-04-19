from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class ReviewModel:
    user_id: str
    user_mobile: str
    service_id: str
    booking_id: str
    rating: int
    comment: str
    images: list
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_document(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "user_mobile": self.user_mobile,
            "service_id": self.service_id,
            "booking_id": self.booking_id,
            "rating": self.rating,
            "comment": self.comment,
            "images": self.images,
            "created_at": self.created_at,
        }
