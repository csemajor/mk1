from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

UserRole = Literal["customer", "banquet_owner", "caterer", "decorator"]


@dataclass(slots=True)
class UserModel:
    password_hash: str
    role: UserRole
    username: str = ""
    email: str = ""
    mobile: str = ""
    primary_identifier: str = ""
    full_name: str = ""
    location: str = ""
    phone: str = ""
    gender: str = ""
    id_proof: str = ""
    profile_completed: str = "false"
    wishlist: list[dict[str, object]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_document(self) -> dict[str, object]:
        return {
            "username": self.username,
            "email": self.email,
            "mobile": self.mobile,
            "primary_identifier": self.primary_identifier,
            "password_hash": self.password_hash,
            "role": self.role,
            "full_name": self.full_name,
            "location": self.location,
            "phone": self.phone,
            "gender": self.gender,
            "id_proof": self.id_proof,
            "profile_completed": self.profile_completed,
            "wishlist": self.wishlist,
            "created_at": self.created_at,
        }
