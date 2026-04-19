from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..core.security import get_current_user
from ..db.database import get_user_collection
from ..schemas.auth_schema import ProfileUpdateRequest, UserResponse

router = APIRouter(prefix="/user", tags=["user"])


def _user_response(doc: dict) -> UserResponse:
    raw = doc.get("profile_completed", "false")
    if isinstance(raw, bool):
        pc = "true" if raw else "false"
    elif isinstance(raw, str):
        pc = "true" if raw.lower() == "true" else "false"
    else:
        pc = "false"

    return UserResponse(
        id=str(doc["_id"]),
        username=doc.get("username", ""),
        email=doc.get("email", ""),
        mobile=doc.get("mobile", doc.get("phone", "")),
        role=doc.get("role", "customer"),
        full_name=doc.get("full_name", ""),
        location=doc.get("location", ""),
        phone=doc.get("phone", ""),
        gender=doc.get("gender", ""),
        id_proof=doc.get("id_proof", ""),
        profile_completed=pc,
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    user_id = current_user.get("sub")
    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=401, detail="Invalid token")

    collection = get_user_collection()

    update_fields: dict[str, object] = {
        "full_name": payload.full_name.strip(),
        "location": payload.location.strip(),
        "profile_completed": "true",
    }
    if payload.email is not None:
        update_fields["email"] = payload.email.strip().lower()
    if payload.phone is not None:
        update_fields["phone"] = payload.phone.strip()
    if payload.gender:
        update_fields["gender"] = payload.gender.strip()
    if payload.id_proof is not None:
        update_fields["id_proof"] = payload.id_proof.strip()

    result = await collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_fields},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await collection.find_one({"_id": ObjectId(user_id)})
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")

    return _user_response(updated)
