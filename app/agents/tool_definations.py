from typing import Any

# Individual tool definitions

TOOL_LOOKUP_CALLER = {
    "type": "function",
    "function": {
        "name": "lookup_caller_by_phone",
        "description": (
            "ALWAYS call this tool first at the start of every call, before speaking to the caller. "
            "Looks up whether the caller's phone number is already registered as a patient. "
            "Returns found=true with the patient's name if they exist, or found=false for new callers. "
            "Use this result to personalise your greeting and decide whether to start a new "
            "registration or offer an update flow."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {
                    "type": "string",
                    "description": (
                        "The caller's phone number as provided in the call metadata. "
                        "Include country code if present. The server normalises it."
                    ),
                }
            },
            "required": ["phone_number"],
        },
    },
}

TOOL_BUILD_CONFIRMATION = {
    "type": "function",
    "function": {
        "name": "build_confirmation_script",
        "description": (
            "Call this tool once all required fields have been collected and BEFORE asking "
            "the caller to confirm their information. "
            "Returns a natural-language readback script you must read aloud word-for-word. "
            "Do NOT improvise the confirmation — always use the returned script."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_data": {
                    "type": "object",
                    "description": "All collected patient fields as a JSON object.",
                    "properties": {
                        "first_name":     {"type": "string"},
                        "last_name":      {"type": "string"},
                        "date_of_birth":  {
                            "type": "string",
                            "description": (
                                "MUST be in YYYY-MM-DD format. "
                                "MUST be a past date — never today or any future date. "
                                "If the caller says a year that is greater than the current year, do NOT call this tool. "
                                "Ask them to confirm their date of birth first. "
                                "Example: 1990-03-01"
                            )
                        },
                        "sex": {
                            "type": "string",
                            "enum": ["Male", "Female", "Other", "Decline to Answer"]
                        },
                        "phone_number":   {
                            "type": "string",
                            "description": "10-digit US phone number, digits only. Example: 2125551234"
                        },
                        "address_line_1": {"type": "string"},
                        "address_line_2": {"type": "string"},
                        "city":           {"type": "string"},
                        "state": {
                            "type": "string",
                            "description": (
                                "MUST be a valid 2-letter US state abbreviation. "
                                "Examples: NY, CA, TX, FL. "
                                "NEVER accept a full state name or country name. "
                                "If the caller says 'New York' convert it to 'NY'. "
                                "If the caller says a country name, ask them for a US state."
                            )
                        },
                        "zip_code": {
                            "type": "string",
                            "description": (
                                "MUST be exactly 5 digits (e.g. 10001) or ZIP+4 format (e.g. 10001-1234). "
                                "NEVER call this tool with fewer than 5 digits. "
                                "If the caller provides fewer than 5 digits, ask them to confirm their full ZIP code."
                            )
                        },
                        "email":                   {"type": "string"},
                        "insurance_provider":      {"type": "string"},
                        "insurance_member_id":     {"type": "string"},
                        "preferred_language":      {"type": "string"},
                        "emergency_contact_name":  {"type": "string"},
                        "emergency_contact_phone": {"type": "string"},
                    },
                    "required": [
                        "first_name", "last_name", "date_of_birth", "sex",
                        "phone_number", "address_line_1", "city", "state", "zip_code",
                    ],
                }
            },
            "required": ["patient_data"],
        },
    },
}

TOOL_REGISTER_PATIENT = {
    "type": "function",
    "function": {
        "name": "register_patient",
        "description": (
            "Save a new patient registration to the database. "
            "ONLY call this after the caller has explicitly confirmed their information is correct. "
            "Never call this proactively or before confirmation. "
            "Returns a speak field you must say to the caller."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_data": {
                    "type": "object",
                    "description": "Complete confirmed patient data. Must include all required fields.",
                    "properties": {
                        "first_name":     {"type": "string"},
                        "last_name":      {"type": "string"},
                        "date_of_birth":  {
                            "type": "string",
                            "description": (
                                "MUST be in YYYY-MM-DD format. "
                                "MUST be a past date — never today or any future date. "
                                "If the caller says a year that is greater than the current year, do NOT call this tool. "
                                "Ask them to confirm their date of birth first. "
                                "Example: 1990-03-01"
                            )
                        },
                        "sex": {
                            "type": "string",
                            "enum": ["Male", "Female", "Other", "Decline to Answer"]
                        },
                        "phone_number":   {
                            "type": "string",
                            "description": "10-digit US phone number, digits only. Example: 2125551234"
                        },
                        "address_line_1": {"type": "string"},
                        "address_line_2": {"type": "string"},
                        "city":           {"type": "string"},
                        "state": {
                            "type": "string",
                            "description": (
                                "MUST be a valid 2-letter US state abbreviation. "
                                "Examples: NY, CA, TX, FL. "
                                "NEVER accept a full state name or country name. "
                                "If the caller says 'New York' convert it to 'NY'. "
                                "If the caller says a country name, ask them for a US state."
                            )
                        },
                        "zip_code": {
                            "type": "string",
                            "description": (
                                "MUST be exactly 5 digits (e.g. 10001) or ZIP+4 format (e.g. 10001-1234). "
                                "NEVER call this tool with fewer than 5 digits. "
                                "If the caller provides fewer than 5 digits, ask them to confirm their full ZIP code."
                            )
                        },
                        "email":                   {"type": "string"},
                        "insurance_provider":      {"type": "string"},
                        "insurance_member_id":     {"type": "string"},
                        "preferred_language":      {"type": "string"},
                        "emergency_contact_name":  {"type": "string"},
                        "emergency_contact_phone": {"type": "string"},
                    },
                    "required": [
                        "first_name", "last_name", "date_of_birth", "sex",
                        "phone_number", "address_line_1", "city", "state", "zip_code",
                    ],
                }
            },
            "required": ["patient_data"],
        },
    },
}

TOOL_UPDATE_PATIENT = {
    "type": "function",
    "function": {
        "name": "update_patient",
        "description": (
            "Update an existing patient's record. Use for returning callers who want to change "
            "their information. Only send the fields that need to change — omit unchanged fields. "
            "Requires the patient_id returned by lookup_caller_by_phone."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "UUID of the existing patient, from lookup_caller_by_phone.",
                },
                "updates": {
                    "type": "object",
                    "description": "Only the fields that need to change. All fields optional.",
                    "properties": {
                        "first_name":              {"type": "string"},
                        "last_name":               {"type": "string"},
                        "date_of_birth":           {"type": "string", "description": "YYYY-MM-DD"},
                        "sex":                     {"type": "string", "enum": ["Male", "Female", "Other", "Decline to Answer"]},
                        "phone_number":            {"type": "string"},
                        "address_line_1":          {"type": "string"},
                        "address_line_2":          {"type": "string"},
                        "city":                    {"type": "string"},
                        "state":                   {"type": "string"},
                        "zip_code":                {"type": "string"},
                        "email":                   {"type": "string"},
                        "insurance_provider":      {"type": "string"},
                        "insurance_member_id":     {"type": "string"},
                        "preferred_language":      {"type": "string"},
                        "emergency_contact_name":  {"type": "string"},
                        "emergency_contact_phone": {"type": "string"},
                    },
                },
            },
            "required": ["patient_id", "updates"],
        },
    },
}

# Combined manifest — pass this list to Vapi

VOICE_AGENT_TOOLS: list[dict[str, Any]] = [
    TOOL_LOOKUP_CALLER,
    TOOL_BUILD_CONFIRMATION,
    TOOL_REGISTER_PATIENT,
    TOOL_UPDATE_PATIENT,
]