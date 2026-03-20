from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from uuid import UUID

from app.api.deps import get_patient_service
from app.core.exceptions import (
    DatabaseError,
    DuplicatePatientError,
    PatientNotFoundError,
)
from app.core.logging import get_logger
from app.schemas.patient import (
    APIResponse,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])
logger = get_logger("api.patients")


#  GET /patients 

@router.get(
    "",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="List all patients",
    description="Returns all active patients. Supports optional query filters.",
    )
def list_patients(
    last_name: Optional[str] = Query(None, description="Partial last name match (case-insensitive)"),
    date_of_birth: Optional[str] = Query(None, description="Exact DOB match in YYYY-MM-DD format"),
    phone_number: Optional[str] = Query(None, description="10-digit US phone number"),
    service: PatientService = Depends(get_patient_service),
    ):
    patients = service.list_patients(
        last_name=last_name,
        date_of_birth=date_of_birth,
        phone_number=phone_number,
    )
    return APIResponse(
        data=[PatientResponse.model_validate(p) for p in patients],
    )


#  GET /patients/:id 

@router.get(
    "/{patient_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single patient",
)
def get_patient(
    patient_id: UUID,
    service: PatientService = Depends(get_patient_service),
):
    try:
        patient = service.get_patient(patient_id)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return APIResponse(data=PatientResponse.model_validate(patient))


#  POST /patients 

@router.post(
    "",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient",
    description=(
        "Creates a new patient record. Returns 409 if the phone number "
        "is already associated with an existing active patient, including "
        "the existing patient_id so the voice agent can offer an update flow."
    ),
)
def create_patient(
    payload: PatientCreate,
    service: PatientService = Depends(get_patient_service),
):
    try:
        patient = service.create_patient(payload)
    except DuplicatePatientError as exc:
        # Surface enough info for the voice agent to handle duplicate detection
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A patient with this phone number already exists.",
                "existing_patient_id": str(exc.existing_id),
                "existing_name": exc.existing_name,
            },
        )
    except DatabaseError as exc:
        logger.error("DB error on create_patient: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save patient record. Please try again.",
        )

    return APIResponse(
        data=PatientResponse.model_validate(patient),
        message=f"Patient registered successfully. ID: {patient.patient_id}",
    )


#  PUT /patients/:id 

@router.put(
    "/{patient_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a patient record (partial update supported)",
)
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    service: PatientService = Depends(get_patient_service),
):
    try:
        patient = service.update_patient(patient_id, payload)
    except DuplicatePatientError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A patient with this phone number already exists.",
                "existing_patient_id": str(exc.existing_id),
                "existing_name": exc.existing_name,
            },
        )
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DatabaseError as exc:
        logger.error("DB error on update_patient %s: %s", patient_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update patient record. Please try again.",
        )

    return APIResponse(
        data=PatientResponse.model_validate(patient),
        message="Patient updated successfully.",
    )


#  DELETE /patients/:id 

@router.delete(
    "/{patient_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a patient record",
    description="Sets deleted_at timestamp. Record is never permanently removed.",
)
def delete_patient(
    patient_id: UUID,
    service: PatientService = Depends(get_patient_service),
):
    try:
        service.delete_patient(patient_id)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DatabaseError as exc:
        logger.error("DB error on delete_patient %s: %s", patient_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete patient record. Please try again.",
        )

    return APIResponse(message=f"Patient {patient_id} has been deleted.")