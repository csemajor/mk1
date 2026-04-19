import os
import re
import uuid
import cloudinary
import cloudinary.uploader
from enum import Enum
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status, File, UploadFile

# Initialize Cloudinary Configuration globally
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "YOUR_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "YOUR_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "YOUR_API_SECRET")
)

from ..core.config import settings

from ..db.database import get_service_collection
from ..models.service_model import ProviderServicesModel, ServiceNodeModel
from ..schemas.service_schema import (
    ServiceCreate,
    ServiceListResponse,
    ServiceResponse,
    UploadImageResponse,
)

router = APIRouter(tags=["services"])

class ServiceSort(str, Enum):
    PRICE_LOW_TO_HIGH = "price_low_to_high"
    PRICE_HIGH_TO_LOW = "price_high_to_low"
    RATING_HIGH_TO_LOW = "rating_high_to_low"


def _normalize_features(raw: object) -> dict:
    def _clean(items: object) -> list[str]:
        if not isinstance(items, list):
            return []
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

    if isinstance(raw, dict):
        predefined = _clean(raw.get("predefined", []))
        custom = _clean(raw.get("custom", []))
    elif isinstance(raw, list):
        # Backward compatibility for older records.
        predefined = _clean(raw)
        custom = []
    else:
        predefined = []
        custom = []

    predefined_keys = {value.casefold() for value in predefined}
    custom = [value for value in custom if value.casefold() not in predefined_keys]

    return {"predefined": predefined, "custom": custom}

def _build_service_pipeline(
    service_type: str | None,
    min_price: float | None,
    max_price: float | None,
    location: str | None,
    rating: float | None,
    search: str | None,
    sort: ServiceSort | None,
) -> list[dict]:
    
    pipeline = [
        {"$unwind": "$services"}
    ]
    
    match_query = {}

    if service_type is not None:
        match_query["services.service_type"] = {"$regex": re.escape(service_type), "$options": "i"}

    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        match_query["services.pricing.amount"] = price_filter

    if location:
        clean_location = location.strip()
        if clean_location:
            match_query["services.location.text"] = {"$regex": re.escape(clean_location), "$options": "i"}

    if rating is not None:
        match_query["services.rating"] = {"$gte": rating}

    if search:
        clean_search = search.strip()
        if clean_search:
            match_query["services.title"] = {"$regex": re.escape(clean_search), "$options": "i"}

    if match_query:
        pipeline.append({"$match": match_query})

    # Sorting
    if sort == ServiceSort.PRICE_LOW_TO_HIGH:
        pipeline.append({"$sort": {"services.pricing.amount": 1}})
    elif sort == ServiceSort.PRICE_HIGH_TO_LOW:
        pipeline.append({"$sort": {"services.pricing.amount": -1}})
    elif sort == ServiceSort.RATING_HIGH_TO_LOW:
        pipeline.append({"$sort": {"services.rating": -1, "services.total_reviews": -1}})
    else:
        pipeline.append({"$sort": {"services.created_at": -1}})

    return pipeline

@router.get("/config/geoapify")
async def get_geoapify_key():
    return {"apiKey": settings.GEOAPIFY_API_KEY}

def _service_response(document: dict) -> ServiceResponse:
    # Handle direct mapped service from unwinding logic or nested fetches
    svc = document if "service_id" in document else document.get("services", {})
    return ServiceResponse(
        service_id=svc.get("service_id", ""),
        provider_mobile=svc.get("provider_mobile", ""),
        role=svc.get("role", ""),
        service_type=svc.get("service_type", ""),
        title=svc.get("title", ""),
        description=svc.get("description", ""),
        location=svc.get("location", {"text": "", "description": ""}),
        pricing=svc.get("pricing", {"amount": 0, "price_type": "", "pricing_description": "", "advance_percentage": 0, "advance_amount": 0}),
        capacity=svc.get("capacity", {"min": 0, "max": 0}),
        features=_normalize_features(svc.get("features", [])),
        images=svc.get("images", {"cover_image_url": "", "gallery_urls": []}),
        availability=svc.get("availability", {"dates": [], "time_slot_type": "", "start_time": "", "end_time": ""}),
        rating=svc.get("rating", 0),
        total_reviews=svc.get("total_reviews", 0),
        created_at=svc.get("created_at"),
    )

@router.post("/services/upload-image", response_model=UploadImageResponse)
async def upload_image(file: UploadFile = File(...)):
    try:
        # Buffer read natively
        result = cloudinary.uploader.upload(file.file)
        secure_url = result.get("secure_url")
        if not secure_url:
            raise Exception("Cloudinary did not return a secure_url.")
        return UploadImageResponse(success=True, url=secure_url)
    except Exception as e:
        # Log error in console and gracefully fail with status 500
        print(f"Cloudinary Upload Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload image to cloud storage.")

@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(payload: ServiceCreate) -> ServiceResponse:
    unique_id = str(uuid.uuid4())
    
    service_node = ServiceNodeModel(
        service_id=unique_id,
        provider_mobile=payload.provider_mobile,
        role=payload.role,
        service_type=payload.service_type,
        title=payload.title,
        description=payload.description,
        location=payload.location.model_dump(),
        pricing=payload.pricing.model_dump(),
        capacity=payload.capacity.model_dump(),
        features=payload.features.model_dump(),
        images=payload.images.model_dump(),
        availability=payload.availability.model_dump(),
        rating=payload.rating,
        total_reviews=payload.total_reviews,
    )

    collection = get_service_collection()
    
    # UPSERT the array pushing natively to the exact array list structure expected by provider_mobile
    result = await collection.update_one(
        {"provider_mobile": payload.provider_mobile},
        {
            "$push": {"services": service_node.to_document()},
            "$setOnInsert": {"created_at": service_node.created_at}
        },
        upsert=True
    )

    return _service_response(service_node.to_document())

@router.get("/services", response_model=ServiceListResponse)
async def get_services(
    service_type: str | None = Query(default=None, alias="type"),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    location: str | None = Query(default=None, min_length=1),
    rating: float | None = Query(default=None, ge=0, le=5),
    search: str | None = Query(default=None, min_length=1),
    sort: ServiceSort | None = Query(default=None),
    provider_mobile: str | None = Query(default=None),
) -> ServiceListResponse:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price cannot be greater than max_price")

    pipeline = []

    # Fast fetch for specific provider before exploding array
    if provider_mobile:
        pipeline.append({"$match": {"provider_mobile": provider_mobile}})

    # Expand the generic pipeline aggregations checking elements
    pipeline.extend(_build_service_pipeline(
        service_type=service_type,
        min_price=min_price,
        max_price=max_price,
        location=location,
        rating=rating,
        search=search,
        sort=sort
    ))

    collection = get_service_collection()
    documents = await collection.aggregate(pipeline).to_list(length=None)
    
    services = [_service_response(doc["services"]) for doc in documents]
    return ServiceListResponse(success=True, count=len(services), data=services)

@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service(service_id: str) -> ServiceResponse:
    collection = get_service_collection()
    
    # Target pipeline isolating inside array
    pipeline = [
        {"$unwind": "$services"},
        {"$match": {"services.service_id": service_id}}
    ]
    documents = await collection.aggregate(pipeline).to_list(length=1)
    
    if not documents:
        raise HTTPException(status_code=404, detail="Service not found")

    return _service_response(documents[0]["services"])

@router.delete("/services/{service_id}", status_code=status.HTTP_200_OK)
async def delete_service(service_id: str, provider_mobile: str = Query(...)) -> dict:
    collection = get_service_collection()
    
    result = await collection.update_one(
        {"provider_mobile": provider_mobile},
        {"$pull": {"services": {"service_id": service_id}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Service not found or unauthorized deletion target.")

    return {"success": True, "message": "Service deleted successfully"}

@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(service_id: str, payload: ServiceCreate) -> ServiceResponse:
    collection = get_service_collection()
    
    update_fields = {
        "services.$.role": payload.role,
        "services.$.service_type": payload.service_type,
        "services.$.title": payload.title,
        "services.$.description": payload.description,
        "services.$.location": payload.location.model_dump(),
        "services.$.pricing": payload.pricing.model_dump(),
        "services.$.capacity": payload.capacity.model_dump(),
        "services.$.features": payload.features.model_dump(),
        "services.$.images": payload.images.model_dump(),
        "services.$.availability": payload.availability.model_dump(),
    }

    result = await collection.update_one(
        {
            "provider_mobile": payload.provider_mobile,
            "services.service_id": service_id
        },
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service not found or unauthorized modify target.")

    return await get_service(service_id)