from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from ..core.security import get_current_user
from ..db.database import get_booking_collection, get_review_collection, get_service_collection, get_user_collection
from ..models.review_model import ReviewModel
from ..schemas.review_schema import (
    ReviewCreateRequest,
    ReviewCreateResponse,
    ReviewListResponse,
    ReviewResponse,
)

router = APIRouter(tags=["reviews"])


def _review_response(document: dict) -> ReviewResponse:
    return ReviewResponse(
        id=str(document["_id"]),
        user_id=str(document.get("user_id", "")),
        user_mobile=str(document.get("user_mobile", "")),
        service_id=str(document.get("service_id", "")),
        booking_id=str(document.get("booking_id", "")),
        rating=int(document.get("rating", 0)),
        comment=str(document.get("comment", "")),
        images=document.get("images", []),
        created_at=document["created_at"],
    )


async def _refresh_service_rating(service_id: str) -> None:
    review_collection = get_review_collection()
    service_collection = get_service_collection()

    summary = await review_collection.aggregate(
        [
            {"$match": {"service_id": service_id}},
            {
                "$group": {
                    "_id": "$service_id",
                    "total_reviews": {"$sum": 1},
                    "avg_rating": {"$avg": "$rating"},
                }
            },
        ]
    ).to_list(length=1)

    if not summary:
        await service_collection.update_many(
            {"services.service_id": service_id},
            {"$set": {"services.$.rating": 0.0, "services.$.total_reviews": 0}},
        )
        return

    stats = summary[0]
    avg_rating = round(float(stats["avg_rating"]), 1)
    total_reviews = int(stats["total_reviews"])

    # Update inside services array (nested document)
    await service_collection.update_many(
        {"services.service_id": service_id},
        {"$set": {"services.$.rating": avg_rating, "services.$.total_reviews": total_reviews}},
    )


@router.post("/reviews", response_model=ReviewCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> ReviewCreateResponse:
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    booking_collection = get_booking_collection()
    review_collection = get_review_collection()
    user_collection = get_user_collection()

    if not ObjectId.is_valid(payload.booking_id):
        raise HTTPException(status_code=400, detail="Invalid booking id")

    service_id = payload.service_id.strip()
    if not service_id:
        raise HTTPException(status_code=400, detail="Service id is required")

    # Validate booking exists and belongs to user
    booking = await booking_collection.find_one({"_id": ObjectId(payload.booking_id)})
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if str(booking.get("user_id")) != user_id:
        raise HTTPException(status_code=403, detail="Not your booking")
    if booking.get("status") != "confirmed":
        raise HTTPException(status_code=400, detail="Booking must be confirmed to review")

    # Validate service_id matches booking
    if str(booking.get("service_id", "")) != service_id:
        raise HTTPException(status_code=400, detail="Service ID does not match booking")

    # Prevent duplicate review per booking
    existing = await review_collection.find_one({"booking_id": payload.booking_id})
    if existing:
        raise HTTPException(status_code=409, detail="You have already reviewed this booking")

    # Get user mobile
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=401, detail="Invalid token")

    user_doc = await user_collection.find_one({"_id": ObjectId(user_id)})
    user_mobile = user_doc.get("mobile", user_doc.get("phone", "")) if user_doc else ""

    # Clamp images to max 3
    images = payload.images[:3]

    review = ReviewModel(
        user_id=user_id,
        user_mobile=user_mobile,
        service_id=service_id,
        booking_id=payload.booking_id,
        rating=payload.rating,
        comment=payload.comment,
        images=images,
    )

    insert_result = await review_collection.insert_one(review.to_document())
    created_review = await review_collection.find_one({"_id": insert_result.inserted_id})
    if created_review is None:
        raise HTTPException(status_code=500, detail="Failed to create review")

    await _refresh_service_rating(service_id)

    return ReviewCreateResponse(success=True, data=_review_response(created_review))


@router.get("/reviews/{service_id}", response_model=ReviewListResponse)
async def get_service_reviews(service_id: str) -> ReviewListResponse:
    service_key = service_id.strip()
    if not service_key:
        raise HTTPException(status_code=400, detail="Invalid service id")

    review_collection = get_review_collection()

    documents = await review_collection.find(
        {"service_id": service_key}
    ).sort("created_at", -1).to_list(length=None)

    return ReviewListResponse(success=True, data=[_review_response(doc) for doc in documents])


@router.get("/reviews/check/{booking_id}")
async def check_review_exists(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Check if a review already exists for this booking."""
    review_collection = get_review_collection()
    existing = await review_collection.find_one({"booking_id": booking_id})
    return {"reviewed": existing is not None}
