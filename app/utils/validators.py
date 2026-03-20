import re
from datetime import date

# ── Constants ────────────────────────────────────────────────────────────────

US_STATES: frozenset[str] = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
})

_NAME_RE = re.compile(r"^[A-Za-z\-']{1,50}$")
_ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")
_ALPHANUM_RE = re.compile(r"^[A-Za-z0-9\s\-]{1,100}$")


# Name validators 

def validate_name(value: str, field_label: str = "Name") -> str:
    """
    1–50 characters, letters only plus hyphens and apostrophes.
    Strips leading/trailing whitespace before validation.
    """
    value = value.strip()
    if not value:
        raise ValueError(f"{field_label} must not be empty")
    if not _NAME_RE.match(value):
        raise ValueError(
            f"{field_label} must be 1–50 characters and contain only letters, "
            "hyphens (-), or apostrophes (')"
        )
    return value


# Date validators 

def validate_date_of_birth(value: date) -> date:
    """Date must be strictly in the past (not today, not future)."""
    if value >= date.today():
        raise ValueError("Date of birth must be in the past")
    return value


# Phone validators 

def normalize_phone(value: str) -> str:
    """
    Strip all non-digit characters and validate as 10-digit US number.
    Returns the normalized 10-digit string (no formatting).

    Accepts: '(646) 555-1234', '646-555-1234', '6465551234', '+1 646 555 1234'
    Rejects: anything that does not reduce to exactly 10 digits.
    """
    digits = re.sub(r"\D", "", value)
    # Handle +1 country code if present
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError(
            f"Phone number must be a valid 10-digit US number "
            f"(got '{value}' → {len(digits)} digits after stripping)"
        )
    return digits


# Address validators 

def validate_state(value: str) -> str:
    """Must be a valid 2-letter US state abbreviation (case-insensitive input)."""
    value = value.strip().upper()
    if value not in US_STATES:
        raise ValueError(
            f"'{value}' is not a valid 2-letter US state abbreviation"
        )
    return value


def validate_zip_code(value: str) -> str:
    """Accepts 5-digit (12345) or ZIP+4 (12345-6789) format."""
    value = value.strip()
    if not _ZIP_RE.match(value):
        raise ValueError(
            "ZIP code must be 5-digit (e.g. 12345) or ZIP+4 (e.g. 12345-6789)"
        )
    return value


def validate_city(value: str) -> str:
    value = value.strip()
    if not (1 <= len(value) <= 100):
        raise ValueError("City must be 1–100 characters")
    return value


def validate_address_line(value: str, field_label: str = "Address") -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_label} must not be empty")
    if len(value) > 255:
        raise ValueError(f"{field_label} must be 255 characters or fewer")
    return value


# Insurance validators 

def validate_insurance_member_id(value: str) -> str:
    """Alphanumeric, spaces, and hyphens only, max 100 chars."""
    value = value.strip()
    if not _ALPHANUM_RE.match(value):
        raise ValueError(
            "Insurance member ID must be alphanumeric (letters, numbers, spaces, hyphens)"
        )
    return value