from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..core.security import get_current_user
from ..db.database import get_service_collection, get_user_collection
from ..schemas.wishlist_schema import (
    WishlistMutationRequest,
    WishlistResponse,
)

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


def _normalize_wishlist(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []

    seen: set[str] = set()
    items: list[dict] = []

    for entry in raw:
        if not isinstance(entry, dict):
            continue

        service_id = str(entry.get("service_id", "")).strip()
        if not service_id or service_id in seen:
            continue

        seen.add(service_id)
        items.append(
            {
                "service_id": service_id,
                "added_at": entry.get("added_at"),
            }
        )

    return items


def _wishlist_response(user_doc: dict) -> WishlistResponse:
    return WishlistResponse(
        success=True,
        user_mobile=str(user_doc.get("mobile") or user_doc.get("phone") or ""),
        wishlist=_normalize_wishlist(user_doc.get("wishlist", [])),
    )


async def _get_authenticated_user_doc(current_user: dict) -> dict:
    user_id = current_user.get("sub")
    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=401, detail="Invalid token")

    collection = get_user_collection()
    user_doc = await collection.find_one({"_id": ObjectId(user_id)})
    if user_doc is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user_doc


@router.get("", response_model=WishlistResponse)
async def get_wishlist(current_user: dict = Depends(get_current_user)) -> WishlistResponse:
    user_doc = await _get_authenticated_user_doc(current_user)
    return _wishlist_response(user_doc)


@router.post("/add", response_model=WishlistResponse)
async def add_to_wishlist(
    payload: WishlistMutationRequest,
    current_user: dict = Depends(get_current_user),
) -> WishlistResponse:
    user_doc = await _get_authenticated_user_doc(current_user)
    service_id = payload.service_id.strip()

    service_collection = get_service_collection()
    service_found = await service_collection.aggregate(
        [
            {"$unwind": "$services"},
            {"$match": {"services.service_id": service_id}},
            {"$limit": 1},
        ]
    ).to_list(length=1)
    if not service_found:
        raise HTTPException(status_code=404, detail="Service not found")

    normalized = _normalize_wishlist(user_doc.get("wishlist", []))
    if any(entry["service_id"] == service_id for entry in normalized):
        return _wishlist_response(user_doc)

    collection = get_user_collection()
    await collection.update_one(
        {"_id": user_doc["_id"]},
        {
            "$push": {
                "wishlist": {
                    "service_id": service_id,
                    "added_at": datetime.now(timezone.utc),
                }
            }
        },
    )

    updated = await collection.find_one({"_id": user_doc["_id"]})
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _wishlist_response(updated)


@router.post("/remove", response_model=WishlistResponse)
async def remove_from_wishlist(
    payload: WishlistMutationRequest,
    current_user: dict = Depends(get_current_user),
) -> WishlistResponse:
    user_doc = await _get_authenticated_user_doc(current_user)
    service_id = payload.service_id.strip()

    collection = get_user_collection()
    await collection.update_one(
        {"_id": user_doc["_id"]},
        {"$pull": {"wishlist": {"service_id": service_id}}},
    )

    updated = await collection.find_one({"_id": user_doc["_id"]})
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _wishlist_response(updated)
