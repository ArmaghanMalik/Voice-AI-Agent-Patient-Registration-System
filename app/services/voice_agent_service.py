import json
import logging
from typing import Any
from pydantic import ValidationError
from dateutil import parser

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DatabaseError,
    DuplicatePatientError,
    PatientNotFoundError,
)
from app.core.logging import get_logger
from app.models.call_transcript import CallTranscript
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.patient_service import PatientService
from app.utils.formatters import format_patient_for_voice_confirmation
from app.utils.validators import normalize_phone

logger = get_logger("services.voice_agent")


class VoiceAgentService:
    """
    Handles every tool call the LLM makes during a phone call.
    One instance per webhook request — receives a scoped DB session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.patient_service = PatientService(db)

    # Tool dispatch — called by the webhook endpoint

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Route a tool call by name to the correct handler.
        Returns a result dict (always includes 'speak' key).
        Catches all exceptions so a crash never silences the caller.
        """
        handlers = {
            "lookup_caller_by_phone":  self._lookup_caller,
            "build_confirmation_script": self._build_confirmation,
            "register_patient":        self._register_patient,
            "update_patient":          self._update_patient,
        }

        handler = handlers.get(tool_name)
        if not handler:
            logger.warning("Unknown tool call: %s", tool_name)
            return {
                "success": False,
                "error": "unknown_tool",
                "speak": "I'm sorry, I encountered a technical issue. Please bear with me.",
            }

        try:
            result = handler(arguments)
            logger.info("Tool call '%s' completed | success=%s", tool_name, result.get("success"))
            return result
        except Exception as exc:
            logger.exception("Unhandled error in tool '%s': %s", tool_name, exc)
            return {
                "success": False,
                "error": "unexpected_error",
                "speak": (
                    "I'm sorry, I ran into a technical issue. "
                    "Please try calling back in a moment."
                ),
            }

    # Tool handlers
    def _lookup_caller(self, args: dict) -> dict:
        """
        Check whether the caller's phone number is already registered.
        Called at the very start of every call (before the agent speaks).
        """
        raw_phone = args.get("phone_number", "")

        try:
            normalized = normalize_phone(raw_phone)
        except ValueError:
            logger.info("lookup_caller: could not normalize phone '%s'", raw_phone)
            return {
                "found": False,
                "speak": None,  # new caller — agent proceeds with registration
            }

        patient = self.patient_service.find_by_phone(normalized)

        if not patient:
            logger.info("lookup_caller: no existing patient for phone %s", normalized)
            return {
                "found": False,
                "speak": None,
            }

        logger.info(
            "lookup_caller: returning caller | id=%s | name=%s %s",
            patient.patient_id, patient.first_name, patient.last_name,
        )
        return {
            "found": True,
            "patient_id": patient.patient_id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "speak": (
                f"Welcome back, {patient.first_name}! "
                "I can see we already have a record for you. "
                "Would you like to update your information, or is there something else I can help you with?"
            ),
        }

    def _build_confirmation(self, args: dict) -> dict:
        """
        Generate the readback script from collected patient data.
        Pure formatting — no DB call. Used in Phase 3 of the conversation.
        """
        patient_data = args.get("patient_data", {})

        if not patient_data:
            return {
                "success": False,
                "speak": "I don't seem to have any information collected yet. Let me ask you a few questions.",
            }

        script = format_patient_for_voice_confirmation(patient_data)
        logger.debug("Built confirmation script for data: %s", list(patient_data.keys()))

        return {
            "success": True,
            "confirmation_script": script,
            "speak": script,
        }

    def _register_patient(self, args: dict) -> dict:
        """
        Save a new patient to the database.
        Called after the caller explicitly confirms their information.
        """
         
        patient_data = args.get("patient_data", {})
        
        pre_errors = []
        import re
        from datetime import date, datetime

        # -- State --
        state = str(patient_data.get("state", "")).strip()
        if state and len(state) != 2:
            pre_errors.append({
                "field": "state",
                "message": f"'{state}' is not valid. State must be a 2-letter US abbreviation like CA or NY."
            })

        # -- ZIP code --
        zip_code = str(patient_data.get("zip_code", "")).strip()
        if zip_code and not re.fullmatch(r"\d{5}(-\d{4})?", zip_code):
            pre_errors.append({
                "field": "zip_code",
                "message": f"'{zip_code}' is not valid. ZIP code must be 5 digits like 12345."
            })

        # -- Date of birth --
        
        dob_raw = str(patient_data.get("date_of_birth", "")).strip()
        if dob_raw:
            parsed_dob = None
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y"):
                try:
                    parsed_dob = datetime.strptime(dob_raw, fmt).date()
                    break
                except ValueError:
                    continue
            
            try:
                parsed_dob = parser.parse(dob_raw).date()
            except:
                parsed_dob = None
            
            if parsed_dob > date.today():
                pre_errors.append({
                    "field": "date_of_birth",
                    "message": f"'{dob_raw}' is a future date. Date of birth cannot be in the future. Please confirm the correct date."
                })
            elif parsed_dob.year < 1900:
                pre_errors.append({
                    "field": "date_of_birth",
                    "message": f"'{dob_raw}' seems too far in the past. Please confirm the correct date of birth."
                })
            else:
                # Normalize to YYYY-MM-DD before Pydantic sees it
                patient_data["date_of_birth"] = parsed_dob.isoformat()

        # -- Return early if pre-validation failed --
        if pre_errors:
            fields = [e["field"] for e in pre_errors]
            speak_text = (
                "Registration failed. "
                f"{len(fields)} field(s) need correction. "
                + " | ".join(
                    f"{e['field'].replace('_', ' ')}: {e['message']}"
                    for e in pre_errors
                )
                + " Please ask the user to correct each field, then call register_patient again."
            )
            return {
                "success": False,
                "status": "FAILED",
                "error": "validation_error",
                "invalid_fields": fields,
                "errors": pre_errors,
                "speak": speak_text,
            }

        
        SEX_MAP = {
            "male": "Male",
            "female": "Female",
            "other": "Other",
            "decline": "Decline to Answer",
            "decline to answer": "Decline to Answer"
        }

        sex = patient_data.get("sex")
        if isinstance(sex, str):
            patient_data["sex"] = SEX_MAP.get(sex.lower().strip(), sex)
        

        # Log the full collected payload — satisfies assessment observability requirement
        logger.info(
            "register_patient: saving new patient | phone=%s | name=%s %s",
            patient_data.get("phone_number"),
            patient_data.get("first_name"),
            patient_data.get("last_name"),
        )
        logger.info("register_patient: full payload: %s", json.dumps(patient_data, default=str))

        try:
            payload = PatientCreate(**patient_data)
            

        except ValidationError as exc:
            field_instructions = []
            logger.warning("register_patient: validation error: %s", exc)

            errors = []
            fields = []

            for err in exc.errors():       
                field = err["loc"][0]
                fields.append(field)

                if field == "state":
                    msg = "Please provide a valid 2-letter US state abbreviation like NY or CA."
                elif field == "zip_code":
                    msg = "ZIP code must be exactly 5 digits like 12345."
                elif field == "date_of_birth":
                    msg = "Please provide a valid past date of birth, for example January 1st 1990."
                elif field == "phone_number":
                    msg = "Please provide a valid 10-digit US phone number."
                else:
                    msg = f"There is an issue with {field.replace('_', ' ')}."

                errors.append({"field": field, "message": msg})

            field_instructions = [
                f"{e['field'].replace('_', ' ')}: {e['message']}" for e in errors
            ]

            speak_text = (
                "Registration failed. "
                f"{len(fields)} field(s) need correction. "
                + " | ".join(field_instructions)
                + " Please ask the user to correct each of these fields, then call register_patient again."
            )

            return {
                "success": False,
                "status": "FAILED",
                "error": "validation_error",
                "invalid_fields": fields,
                "errors": errors,
                "speak": speak_text,
            }

        try:
            patient = self.patient_service.create_patient(payload)
            logger.info("register_patient: success | patient_id=%s", patient.patient_id)

            return {
                "success": True,
                "status": "COMPLETED",
                "patient_id": patient.patient_id,
                "speak": (
                    f"You're all set, {patient.first_name}! "
                    "Your registration is complete. "
                    "Is there anything else I can help you with today?"
                ),
            }

        except DuplicatePatientError as exc:
            logger.warning(
                "register_patient: duplicate detected | phone=%s | existing=%s '%s'",
                exc.phone_number, exc.existing_id, exc.existing_name,
            )
            return {
                "success": False,
                "status": "FAILED",
                "error": "duplicate_patient",
                "existing_patient_id": exc.existing_id,
                "existing_name": exc.existing_name,
                "assistant_response": (
                f"It looks like we already have a record for {exc.existing_name}. "
                "Would you like to update your existing information instead?"
            )
                # "speak": (
                #     f"It looks like we already have a record on file for {exc.existing_name}. "
                #     "Would you like to update your existing information instead?"
                # )
            }

        except DatabaseError as exc:
            logger.error("register_patient: database error: %s", exc)
            return {
                "success": False,
                "status": "FAILED",
                "error": "database_error",
                "speak": (
                    "I'm very sorry — I'm having trouble saving your information right now "
                    "due to a technical issue. Your information has not been saved. "
                    "Please call us back in a few minutes and we will be happy to help you."
                ),
            }

    def _update_patient(self, args: dict) -> dict:
        """
        Update an existing patient record for a returning caller.
        Only the fields present in 'updates' are written.
        """
        patient_id = args.get("patient_id", "")
        updates = args.get("updates", {})
        # updates = args

        if not patient_id:
            return {
                "success": False,
                "speak": "I wasn't able to find your existing record. Let me register you as a new patient instead.",
            }
        print(f"UPDATES : {updates}")
        if not updates:
            return {
                "success": False,
                "speak": "It looks like there's nothing to update. Would you like to change something specific?",
            }

        logger.info(
            "update_patient: updating patient_id=%s | fields=%s",
            patient_id, list(updates.keys()),
        )

        try:
            payload = PatientUpdate(**updates)
        except Exception as exc:
            logger.warning("update_patient: validation error: %s", exc)
            return {
                "success": False,
                "status": "FAILED",
                "error": "validation_error",
                "speak": "I wasn't able to update your record due to a data issue. Could we go over the changes again?",
            }

        try:
            patient = self.patient_service.update_patient(patient_id, payload)
            return {
                "success": True,
                "status": "COMPLETED",
                "patient_id": patient.patient_id,
                "speak": (
                    f"I've updated your record, {patient.first_name}. "
                    "Is there anything else I can help you with?"
                ),
            }

        except PatientNotFoundError:
            return {
                "success": False,
                "status": "FAILED",
                "error": "not_found",
                "speak": "I wasn't able to find your existing record. Let me register you as a new patient instead.",
            }

        except DatabaseError as exc:
            logger.error("update_patient: database error: %s", exc)
            return {
                "success": False,
                "status": "FAILED",
                "error": "database_error",
                "speak": "I'm sorry, I wasn't able to update your record right now. Please try again shortly.",
            }

    # Transcript persistence
    def save_transcript(
        self,
        vapi_call_id: str | None,
        caller_phone: str | None,
        transcript: str | None,
        patient_id: str | None,
        registration_completed: bool,
        was_returning_caller: bool,
        was_update_call: bool,
        collected_data: dict | None,
        duration_seconds: float | None,
    ) -> None:
        """
        Persist the end-of-call transcript to the call_transcripts table.
        Called from the end-of-call webhook handler.
        Non-fatal — if this fails, we log it but don't crash.
        """
        try:
            record = CallTranscript(
                vapi_call_id=vapi_call_id,
                caller_phone_number=caller_phone,
                transcript=transcript,
                patient_id=patient_id,
                registration_completed=registration_completed,
                was_returning_caller=was_returning_caller,
                was_update_call=was_update_call,
                collected_data_snapshot=json.dumps(collected_data, default=str) if collected_data else None,
                call_duration_seconds=int(duration_seconds) if duration_seconds else None,
            )
            self.db.add(record)
            self.db.commit()
            logger.info(
                "Transcript saved | call_id=%s | patient_id=%s | completed=%s | duration=%ss",
                vapi_call_id, patient_id, registration_completed, duration_seconds,
            )
        except Exception as exc:
            self.db.rollback()
            logger.exception("Failed to save transcript for call %s: %s", vapi_call_id, exc)