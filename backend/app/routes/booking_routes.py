from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..core.security import get_current_user
from ..db.database import get_booking_collection, get_service_collection, get_review_collection
from ..models.booking_model import BookingModel
from ..schemas.booking_schema import (
    BookingCreateRequest,
    BookingCreateResponse,
    BookingListResponse,
    MyBookingItem,
    MyBookingListResponse,
    BookingResponse,
)

from datetime import datetime, timezone

router = APIRouter(tags=["bookings"])


def _booking_response(document: dict) -> BookingResponse:
    return BookingResponse(
        id=str(document.get("_id", "")),
        user_id=str(document.get("user_id", "")),
        service_id=str(document.get("service_id", "")),
        provider_mobile=str(document.get("provider_mobile", "")),
        user_mobile=str(document.get("user_mobile", "")),
        user_location=document.get("user_location", {}),
        date=document.get("date"),
        slot=document.get("slot"),
        total_price=float(document.get("total_price", 0)),
        advance_paid=float(document.get("advance_paid", 0.0)),
        status=str(document.get("status", "confirmed")),
        created_at=document.get("created_at"),
        cancelled_at=document.get("cancelled_at"),
    )


@router.post("/book", response_model=BookingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> BookingCreateResponse | JSONResponse:
    auth_user_id = current_user.get("sub")
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    service_collection = get_service_collection()
    booking_collection = get_booking_collection()
    from ..db.database import get_user_collection
    user_collection = get_user_collection()

    user_doc = await user_collection.find_one({"_id": ObjectId(auth_user_id)})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    user_mobile = user_doc.get("mobile", user_doc.get("phone", ""))

    # Find embedded service document using the unwound aggregation
    pipeline = [
        {"$unwind": "$services"},
        {"$match": {"services.service_id": payload.service_id}}
    ]
    documents = await service_collection.aggregate(pipeline).to_list(1)
    
    if not documents:
        raise HTTPException(status_code=404, detail="Service not found")

    provider_doc = documents[0]
    service = provider_doc["services"]

    booking_date = payload.date.isoformat()
    requested_slot = payload.slot

    available_dates = service.get("availability", {}).get("dates", [])
    if booking_date not in available_dates:
        raise HTTPException(status_code=404, detail="Date not strictly available for this service config")

    # Conflict check inside booking table rather than service config directly
    existing_booking = await booking_collection.find_one({
        "service_id": payload.service_id,
        "date": booking_date,
        "slot": requested_slot,
        "status": "confirmed"
    })

    if existing_booking:
         return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"success": False, "message": "Slot already booked."},
        )

    try:
        booking = BookingModel(
            user_id=auth_user_id,
            service_id=payload.service_id,
            provider_mobile=provider_doc.get("provider_mobile", ""),
            user_mobile=user_mobile,
            user_location=user_doc.get("location_data", {}),
            date=booking_date,
            slot=requested_slot,
            total_price=float(service.get("pricing", {}).get("amount", 0)),
            advance_paid=payload.advance_paid,
        )
        insert_result = await booking_collection.insert_one(booking.to_document())
        created_booking = await booking_collection.find_one({"_id": insert_result.inserted_id})
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create booking") from exc

    return BookingCreateResponse(success=True, data=_booking_response(created_booking))


@router.get("/bookings/me", response_model=MyBookingListResponse)
async def get_my_bookings(current_user: dict = Depends(get_current_user)) -> MyBookingListResponse:
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    booking_collection = get_booking_collection()
    service_collection = get_service_collection()

    review_collection = get_review_collection()

    documents = await booking_collection.find({"user_id": user_id}).sort("created_at", -1).to_list(
        length=None
    )

    service_ids = list(set([doc.get("service_id") for doc in documents if doc.get("service_id")]))
    booking_ids_raw = [str(doc.get("_id")) for doc in documents]

    # Pre-fetch reviewed booking IDs
    reviewed_booking_ids = set()
    if booking_ids_raw:
        reviews = await review_collection.find(
            {"booking_id": {"$in": booking_ids_raw}},
            {"booking_id": 1}
        ).to_list(length=None)
        for r in reviews:
            if r.get("booking_id"):
                reviewed_booking_ids.add(r["booking_id"])

    service_map: dict[str, dict] = {}
    if service_ids:
        # Aggregation pipeline to fetch mapped services
        pipeline = [
            {"$unwind": "$services"},
            {"$match": {"services.service_id": {"$in": service_ids}}}
        ]
        provider_docs = await service_collection.aggregate(pipeline).to_list(length=None)
        
        for pdoc in provider_docs:
            svc = pdoc["services"]
            svc["provider_mobile"] = pdoc.get("provider_mobile")
            service_map[svc["service_id"]] = svc

    items: list[MyBookingItem] = []
    for booking in documents:
        b_id_str = str(booking.get("_id", ""))
        service_key = str(booking.get("service_id", ""))
        service = service_map.get(service_key, {})
        
        provider_contact = service.get("provider_mobile", "Not provided")
        
        items.append(
            MyBookingItem(
                booking_id=b_id_str,
                service_id=service_key,
                service_name=service.get("title", "Service"),
                date=str(booking.get("date", "")),
                slot=str(booking.get("slot", "")),
                price=float(booking.get("total_price", 0)),
                advance_paid=float(booking.get("advance_paid", 0.0)),
                provider_contact=str(provider_contact),
                status=str(booking.get("status", "confirmed")),
                is_reviewed=b_id_str in reviewed_booking_ids,
            )
        )

    return MyBookingListResponse(success=True, data=items)


@router.get("/bookings/{service_id}", response_model=BookingListResponse)
async def get_service_bookings(service_id: str) -> BookingListResponse:
    booking_collection = get_booking_collection()
    documents = await booking_collection.find({"service_id": service_id}).sort(
        "created_at", -1
    ).to_list(length=None)

    bookings = [_booking_response(document) for document in documents]
    return BookingListResponse(success=True, data=bookings)

@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
async def booking_cancel(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
) -> BookingResponse:
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=400, detail="Invalid booking id")

    booking_collection = get_booking_collection()

    booking = await booking_collection.find_one({"_id": ObjectId(booking_id)})
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized to cancel this booking")

    if booking.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Booking is already cancelled")

    await booking_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc)
        }}
    )

    updated_booking = await booking_collection.find_one({"_id": ObjectId(booking_id)})
    return _booking_response(updated_booking)
