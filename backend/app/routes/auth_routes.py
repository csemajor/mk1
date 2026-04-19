from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from ..core.security import create_access_token, hash_password, verify_password
from ..db.database import get_user_collection
from ..models.user_model import UserModel
from ..schemas.auth_schema import (
    AuthResponse,
    LoginPhoneRequest,
    LoginRequest,
    ProviderLoginRequest,
    ProviderRegisterRequest,
    RegisterPhoneRequest,
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(doc: dict) -> UserResponse:
    """Build UserResponse from MongoDB document.
    profile_completed is stored as string "true" or "false" in the DB.
    For old docs that may have bool or missing field, we normalize to string.
    """
    raw = doc.get("profile_completed", "false")
    # Normalize: bool True -> "true", bool False -> "false", missing -> "false"
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


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> AuthResponse:
    username = payload.username.strip()
    email = payload.email.strip().lower()

    if not username and not email:
        raise HTTPException(status_code=400, detail="Username or email is required")

    if username and len(username) < 4:
        raise HTTPException(status_code=400, detail="Username must be at least 4 characters")

    collection = get_user_collection()

    # Check for duplicates
    if username:
        existing = await collection.find_one({"username": username})
        if existing:
            raise HTTPException(status_code=409, detail="Username already taken")

    if email:
        existing = await collection.find_one({"email": email})
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

    # Determine primary identifier
    primary_identifier = email if email else username

    user = UserModel(
        username=username,
        email=email,
        primary_identifier=primary_identifier,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        profile_completed="false",
    )

    result = await collection.insert_one(user.to_document())
    created = await collection.find_one({"_id": result.inserted_id})

    if created is None:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user_resp = _user_response(created)
    token = create_access_token({"sub": str(created["_id"]), "role": user_resp.role})

    return AuthResponse(success=True, token=token, user=user_resp)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    username = payload.username.strip()
    email = payload.email.strip().lower()

    if not username and not email:
        raise HTTPException(status_code=400, detail="Username or email is required")

    collection = get_user_collection()

    query: dict[str, str] = {}
    if email:
        query["email"] = email
    else:
        query["username"] = username

    user_doc = await collection.find_one(query)

    if user_doc is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_resp = _user_response(user_doc)
    token = create_access_token({"sub": str(user_doc["_id"]), "role": user_resp.role})

    return AuthResponse(success=True, token=token, user=user_resp)


@router.post("/register-phone", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_phone(payload: RegisterPhoneRequest) -> AuthResponse:
    mobile = payload.mobile.strip()

    collection = get_user_collection()
    existing = await collection.find_one({"$or": [{"mobile": mobile}, {"phone": mobile}]})
    if existing:
        raise HTTPException(status_code=409, detail="Mobile number already registered")

    user = UserModel(
        mobile=mobile,
        primary_identifier=mobile,
        password_hash=hash_password(payload.password),
        role="customer",
        profile_completed="false",
    )

    try:
        result = await collection.insert_one(user.to_document())
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Mobile number already registered") from exc

    created = await collection.find_one({"_id": result.inserted_id})
    if created is None:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user_resp = _user_response(created)
    token = create_access_token({"sub": str(created["_id"]), "role": user_resp.role})
    return AuthResponse(success=True, token=token, user=user_resp)


@router.post("/login-phone", response_model=AuthResponse)
async def login_phone(payload: LoginPhoneRequest) -> AuthResponse:
    mobile = payload.mobile.strip()
    collection = get_user_collection()

    user_doc = await collection.find_one({"$or": [{"mobile": mobile}, {"phone": mobile}]})
    if user_doc is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user_doc.get("role") != "customer":
        raise HTTPException(status_code=403, detail="This login is only for customers")

    if not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_resp = _user_response(user_doc)
    token = create_access_token({"sub": str(user_doc["_id"]), "role": user_resp.role})
    return AuthResponse(success=True, token=token, user=user_resp)


@router.post("/provider-register", status_code=status.HTTP_201_CREATED)
async def provider_register(payload: ProviderRegisterRequest) -> dict:
    mobile = payload.mobile.strip()
    collection = get_user_collection()

    existing = await collection.find_one({"$or": [{"mobile": mobile}, {"phone": mobile}]})
    if existing:
        raise HTTPException(status_code=409, detail="Mobile number already registered")

    user = UserModel(
        mobile=mobile,
        primary_identifier=mobile,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        full_name=payload.full_name.strip(),
        location=payload.location.strip(),
        email=(payload.email or "").strip().lower(),
        id_proof=(payload.id_proof or "").strip(),
        profile_completed="true",
    )

    try:
        await collection.insert_one(user.to_document())
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Mobile number already registered") from exc

    return {"success": True, "message": "Account created. Please login."}


@router.post("/provider-login", response_model=AuthResponse)
async def provider_login(payload: ProviderLoginRequest) -> AuthResponse:
    mobile = payload.mobile.strip()
    collection = get_user_collection()

    user_doc = await collection.find_one({"$or": [{"mobile": mobile}, {"phone": mobile}]})
    if user_doc is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user_doc.get("role") == "customer":
        raise HTTPException(status_code=403, detail="This login is only for service providers")

    if not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_resp = _user_response(user_doc)
    token = create_access_token({"sub": str(user_doc["_id"]), "role": user_resp.role})
    return AuthResponse(success=True, token=token, user=user_resp)
