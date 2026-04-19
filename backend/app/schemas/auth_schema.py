import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RoleEnum(str, Enum):
    CUSTOMER = "customer"
    BANQUET_OWNER = "banquet_owner"
    CATERER = "caterer"
    DECORATOR = "decorator"


class RegisterRequest(BaseModel):
    username: str = ""
    email: str = ""
    password: str = Field(..., min_length=3)
    role: RoleEnum = RoleEnum.CUSTOMER


class LoginRequest(BaseModel):
    username: str = ""
    email: str = ""
    password: str


class RegisterPhoneRequest(BaseModel):
    mobile: str
    password: str = Field(..., min_length=3)

    @field_validator("mobile")
    @classmethod
    def mobile_must_be_digits(cls, v: str) -> str:
        cleaned = v.strip()
        if not re.fullmatch(r"\d{10}", cleaned):
            raise ValueError("Mobile must be exactly 10 digits")
        return cleaned


class LoginPhoneRequest(BaseModel):
    mobile: str
    password: str

    @field_validator("mobile")
    @classmethod
    def login_mobile_must_be_digits(cls, v: str) -> str:
        cleaned = v.strip()
        if not re.fullmatch(r"\d{10}", cleaned):
            raise ValueError("Mobile must be exactly 10 digits")
        return cleaned


class ProviderRegisterRequest(BaseModel):
    mobile: str
    password: str = Field(..., min_length=3)
    full_name: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    role: RoleEnum
    email: Optional[str] = ""
    id_proof: Optional[str] = ""

    @field_validator("mobile")
    @classmethod
    def provider_mobile_must_be_digits(cls, v: str) -> str:
        cleaned = v.strip()
        if not re.fullmatch(r"\d{10}", cleaned):
            raise ValueError("Mobile must be exactly 10 digits")
        return cleaned

    @field_validator("role")
    @classmethod
    def role_must_be_provider(cls, v: RoleEnum) -> RoleEnum:
        if v == RoleEnum.CUSTOMER:
            raise ValueError("Customers cannot register as providers")
        return v


class ProviderLoginRequest(BaseModel):
    mobile: str
    password: str

    @field_validator("mobile")
    @classmethod
    def provider_login_mobile(cls, v: str) -> str:
        cleaned = v.strip()
        if not re.fullmatch(r"\d{10}", cleaned):
            raise ValueError("Mobile must be exactly 10 digits")
        return cleaned


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = ""
    id_proof: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def phone_must_be_digits(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            return ""
        if not re.fullmatch(r"\d{10}", cleaned):
            raise ValueError("Phone must be exactly 10 digits")
        return cleaned

    @field_validator("email")
    @classmethod
    def email_format_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip().lower()
        if not cleaned:
            return ""
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", cleaned):
            raise ValueError("Email format is invalid")
        return cleaned


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    mobile: str = ""
    role: str
    full_name: str = ""
    location: str = ""
    phone: str = ""
    gender: str = ""
    id_proof: str = ""
    profile_completed: str = "false"


class AuthResponse(BaseModel):
    success: bool = True
    token: str
    user: UserResponse
