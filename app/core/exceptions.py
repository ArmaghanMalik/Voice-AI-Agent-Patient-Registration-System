"""
Domain-specific exceptions.
 
Each exception maps to a well-defined HTTP status code in the API layer.
The service layer raises these; the endpoint layer catches and converts them.
"""

class PatientNotFoundError(Exception):
    """Raised when patient_id does not exists
    """
    def __init__(self, patient_id: str):
        self.patient_id = patient_id
        super().__init__(f"Patient '{patient_id}' not found")

class DuplicatePatientError(Exception):
    """Raised when a new registration uses a phone number already on record.
    Carries the existing record's ID and name so the voice agent can relay it.
    """
    def __init__(self, phone_number: str, existing_id: str, existing_name: str):
        self.phone_number = phone_number
        self.existing_id = existing_id
        self.existing_name = existing_name
        super().__init__(
            f"Patient with phone '{phone_number}' already exists: "
            f"'{existing_name}' (id={existing_id})"
        )

class ValidationError(Exception):
    """Raised by the service layer for domain-level validation failures.
    """
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message 
        super().__init__(f"Validation failed for '{field}': {message}")

class DatabaseError(Exception):
    """Wraps unexpected database-level errors so they don't leak raw SQLAlchemy details."""
    pass
        