import re
from datetime import date, datetime
from typing import Optional, List, Union
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from app.models.patient import SexEnum
from uuid import UUID

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY","DC",
}

NAME_RE = re.compile(r"^[A-Za-z\-']{1,50}$")
PHONE_RE = re.compile(r"^\d{10}$")
ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")

def _validate_name(v: str, field: str) -> str:
    v = v.strip()
    if not NAME_RE.match(v):
        raise ValueError(
            f"{field} must be 1-50 chars, letters, hyphens, or apostrophes only"
        )
    return v

def _validate_phone(v: str) -> str:
    digits = re.sub(r"\D", "", v)
    if len(digits) != 10:
        raise ValueError("Phone number must be a valid 10-digit US number")
    return digits

class PatientBase(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    sex: SexEnum
    phone_number: str
    email: Optional[EmailStr] = None
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state:str
    zip_code: str
    preferred_language: str = "English"

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        return _validate_name(v, "First name")
    
    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: str) -> str:
        return _validate_name(v, "Last name")
    
    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("Date of birth must be in the Past")
        return v
    
    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        return _validate_phone(v)
    
    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: str) -> str:
        v = v.strip()
        if not ZIP_RE.match(v):
            raise ValueError("ZIP code must be 5-digit or ZIP+4 format (e.g. 12345 or 12345-6789)")
        return v
    
    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in US_STATES:
            raise ValueError(f"'{v}' is not a valid 2-letter US state abbreviation")
        return v
    
    @field_validator("city")
    @classmethod
    def validate_city(cls, v: str) -> str:
        v = v.strip()
        if not (1 <= len(v) <= 100):
            raise ValueError("City must be 1–100 characters")
        return v
    
    @field_validator("address_line_1")
    @classmethod
    def validate_address(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Address line 1 is required")
        return v
    
class PatientCreate(PatientBase):
    pass

class PatientUpdate(BaseModel):
    """All fields optional for partial updates."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[SexEnum] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address_line_1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    preferred_language: Optional[str] = None

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: Optional[str]) -> Optional[str]:
        return _validate_name(v, "First name") if v else v

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: Optional[str]) -> Optional[str]:
        return _validate_name(v, "Last name") if v else v

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v) if v else v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        v = v.upper().strip()
        if v not in US_STATES:
            raise ValueError(f"'{v}' is not a valid 2-letter US state abbreviation")
        return v

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if not ZIP_RE.match(v.strip()):
            raise ValueError("ZIP code must be 5-digit or ZIP+4 format")
        return v.strip()

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: Optional[date]) -> Optional[date]:
        if v and v >= date.today():
            raise ValueError("Date of birth must be in the past")
        return v
    
class PatientResponse(PatientBase):
    patient_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class APIResponse(BaseModel):
    data: Optional[Union[PatientResponse, List[PatientResponse]]] = None
    error: Optional[str] = None
    message: Optional[str] = None