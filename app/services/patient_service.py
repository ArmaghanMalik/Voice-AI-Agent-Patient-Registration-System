from sqlalchemy.orm import Session 
from app.core.logging import get_logger
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from datetime import datetime, timezone
from typing import Optional
from app.models.patient import Patient

from app.core.exceptions import(
    PatientNotFoundError,
    DuplicatePatientError,
    DatabaseError,
)

logger = get_logger("services.patient")

class PatientService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_patient(self, patient_id: str) -> Patient:
        """
        Fetch a single active patient.
        Raises PatientNotFoundError if not found or soft-deleted.
        """
        patient = self.get_by_id(patient_id)
        if not patient:
            raise PatientNotFoundError(patient_id)
        return patient

    def list_patients(
            self,
            last_name: str | None = None,
            date_of_birth: str | None = None,
            phone_number: str | None = None,
    ) -> list[Patient]:
        """Return all active patients, optionally filtered."""
        patients = self.list_all(
            last_name = last_name,
            date_of_birth =date_of_birth,
            phone_number = phone_number,
        )
        logger.info(
            "Listed %d patients | filters: last_name=%s dob=%s phone=%s",
            len(patients), last_name, date_of_birth, phone_number,
        )
        return patients
    
    def create_patient(self, payload: PatientCreate) -> Patient:
        """
        Register a new patient.
 
          1. Phone number must be unique among active patients.
             If a match exists, raises DuplicatePatientError — the voice agent
             intercepts this and offers the caller an update flow instead.
 
        Raises:
          DuplicatePatientError — phone number already registered
          DatabaseError         — unexpected persistence failure
        """
        existing = self.get_by_phone(payload.phone_number)
        if existing:
            logger.warning(
                "Duplicate registration attempt | phone=%s | existing_id=%s | existing_name=%s %s",
                payload.phone_number, existing.patient_id,
                existing.first_name, existing.last_name,
            )
            raise DuplicatePatientError(
                phone_number=payload.phone_number,
                existing_id=existing.patient_id,
                existing_name=f"{existing.first_name} {existing.last_name},"
            )
        
        try:
            patient = self.create(payload.model_dump())
            self.db.commit()
            logger.info(
                "Patient registered | id=%s | name=%s | phone=%s",
                patient.patient_id, patient.first_name,
                patient.last_name, patient.phone_number,
            )
            # Log the full payload so call data is always in the audit trail
            logger.debug("Regitration payload: %s", payload.model_dump())
            return patient
        except Exception as exc:
            self.db.rollback()
            logger.exception("Database error during patient cration: %s", exc)
            raise DatabaseError("Failed to presist patient record") from exc
        
    def update_patient(self, patient_id: str, payload: PatientUpdate) -> Patient:
        """update an existing patient record.

        Only the fields explicitly set in the payload are written.
        Fields omitted from the request body are left unchanged.

        Raises:
        PatientNotFoundError  — patient does not exist or is deleted
        DatabaseError         — unexpected persistence failure
        """
        patient = self.get_patient(patient_id)

        existing = self.get_by_phone(payload.phone_number)
        if existing and existing.patient_id != patient_id:
            raise DuplicatePatientError(
                phone_number=payload.phone_number,
                existing_id=existing.patient_id,
                existing_name=f"{existing.first_name} {existing.last_name}"
            )
        # model_dump(exclude_unset=True) gives us only the fields the caller sent
        updates = payload.model_dump(exclude_unset=True)

        try:
            patient = self.update(patient, updates)
            self.db.commit()
            logger.info(
                "Patient updated | id=%s | fields=%s",
                patient_id, list(updates.keys()),
            )
            return patient
        except Exception as exc:
            self.db.rollback()
            logger.exception("Databse error during patient update: %s", exc)
            raise DatabaseError("Failed to update patient record") from exc
        
    def delete_patient(self, patient_id: str) -> None:
        """
        Soft-delete a patient record (sets is_deleted=True, deleted_at=now).
        Hard-delete is intentionally not supported.
 
        Raises:
          PatientNotFoundError — patient does not exist or already deleted
          DatabaseError        — unexpected persistence failure
        """
        patient = self.get_patient(patient_id)

        try:
            self.soft_delete(patient)
            self.db.commit()
            logger.info("Patient deleted | id=%s", patient_id)
        except Exception as exc:
            self.db.rollback()
            logger.exception("Database error during deletion: %s", exc)
            raise DatabaseError("Failed to delete patient record") from exc
        
    def find_by_phone(self, phone_number: str) -> Patient:
        """
        Look up an active patient by phone number.
        Returns None if not found — does NOT raise.
        Used by the voice agent to detect returning callers.
        """
        from app.utils.validators import normalize_phone

        try:
            normalized = normalize_phone(phone_number)
        except ValueError:
            return None
        return self.get_by_phone(normalized)
    
    # Read 
    def get_by_id(self, patient_id: str) -> Optional[Patient]:
        """Return an active (non-deleted) patient by primary key, or None."""
        return(
            self.db.query(Patient).filter(Patient.patient_id == patient_id, Patient.is_deleted.is_(False)).first()
        )
    
    def get_by_phone(self, phone_number: str) -> Optional[Patient]:
        """
        Return an active patient with the given normalized phone number, or None.
        Used for duplicate detection during registration.
        """
        return(
            self.db.query(Patient).filter(Patient.phone_number == phone_number, Patient.is_deleted.is_(False)).first()
        )
    
    def list_all(
            self,
            last_name: Optional[str] = None,
            date_of_birth: Optional[str] = None,
            phone_number: Optional[str] = None,
    ) -> list[Patient]:
        """Return all active patients, with optional filters."""
        query =  self.db.query(Patient).filter(Patient.is_deleted.is_(False))

        if last_name:
            query = query.filter(Patient.last_name.ilike(f"%{last_name.strip()}%"))

        if date_of_birth:
             query = query.filter(Patient.date_of_birth == date_of_birth)

        if phone_number:
            import re
            digits = re.sub(r"\D", "", phone_number)
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]
            query = query.filter(Patient.phone_number == digits)
 
        return query.order_by(Patient.created_at.desc()).all()
    
    # Write
    def create(self, data: dict) -> Patient:
        """
        Persist a new patient record.
        data is a plain dict of field→value
        """
        patient = Patient(**data)
        self.db.add(patient)
        self.db.flush() # assigns patient_id without committing the transaction
        self.db.refresh(patient)
        logger.debug("Flushed new patient to session: id=%s", patient.patient_id)
        return patient
    
    def update(self, patient: Patient, updates: dict) -> Patient:
        """
        Apply a partial update to an existing patient record.
        updates is a dict of only the fields that should change.
        """
        for field, value in updates.items():
            setattr(patient, field, value)
        self.db.flush()
        self.db.refresh(patient)
        logger.debug(
            "Flushed update to patient %s | fields=%s", patient.patient_id, list(updates.keys()),
        )
        return patient
    
    def soft_delete(self, patient: Patient) -> Patient:
        """
        Mark a patient as deleted. Never hard-deletes
        """
        patient.is_deleted = True
        patient.deleted_at = datetime.now(timezone.utc)
        self.db.flush()
        self.db.refresh(patient)
        logger.debug("Flushed soft-delete for patient %s", patient.patient_id)
        return patient
    

    
    


    