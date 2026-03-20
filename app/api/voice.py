
import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.vapi import (
    ToolCallPayload,
    ToolCallResponse,
    ToolCallResult,
    EndOfCallPayload,
)
from app.services.voice_agent_service import VoiceAgentService

# Reuse the same get_db from deps.py
from app.api.deps import get_db

router = APIRouter(prefix="/voice", tags=["Voice Agent"])
logger = get_logger("api.voice")
settings = get_settings()

# Webhook signature verification

def _verify_vapi_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Vapi signs webhooks using HMAC-SHA256.
    If VAPI_WEBHOOK_SECRET is set, we verify every incoming request.
    If not set, we skip verification (dev/ngrok mode).

    Vapi sends the signature as:  x-vapi-signature: sha256=<hex>
    """
    secret = getattr(settings, "vapi_webhook_secret", "")
    if not secret:
        return True  # verification disabled in dev

    if not signature_header:
        logger.warning("Missing Vapi signature header")
        return False

    expected = "sha256=" + hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


# POST /voice/tool-call
@router.post(
    "/tool-call",
    response_model=ToolCallResponse,
    status_code=status.HTTP_200_OK,
    summary="Vapi tool-call webhook",
    description=(
        "Receives tool invocations from the Vapi LLM during a live phone call. "
        "Executes the requested tool and returns the result to the LLM."
    ),
)
async def handle_tool_call(
    request: Request,
    x_vapi_signature: str | None = Header(None, alias="x-vapi-signature"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()

    # Signature verification
    if not _verify_vapi_signature(raw_body, x_vapi_signature):
        logger.warning("Vapi webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    logger.debug("Received tool-call webhook: %s", json.dumps(body)[:500])

    # Extract tool calls from Vapi's message envelope
    message = body.get("message", {})
    tool_calls = message.get("toolCallList", [])

    if not tool_calls:
        # logger.warning("tool-call webhook received with empty toolCallList")
        return ToolCallResponse(results=[])

    # Extract caller phone from call metadata (used by lookup_caller_by_phone)
    call_meta = message.get("call", {})
    caller_phone = (
        call_meta.get("customer", {}).get("number", "")
        if call_meta else ""
    )

    service = VoiceAgentService(db)
    results: list[ToolCallResult] = []

    for tool_call in tool_calls:
        call_id   = tool_call.get("id", "")
        function  = tool_call.get("function", {})
        tool_name = function.get("name", "")
        arguments = function.get("arguments", {})

        # If arguments came in as a JSON string (some Vapi versions do this), parse it
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        # Inject caller_phone into lookup_caller_by_phone if not provided by LLM
        if tool_name == "lookup_caller_by_phone" and not arguments.get("phone_number"):
            arguments["phone_number"] = caller_phone
            logger.debug("Injected caller_phone=%s into lookup_caller_by_phone", caller_phone)

        logger.info(
            "Executing tool | name=%s | call_id=%s | args_keys=%s",
            tool_name, call_id, list(arguments.keys()),
        )

        result_dict = service.dispatch(tool_name, arguments)

        results.append(
            ToolCallResult(
                toolCallId=call_id,
                result=json.dumps({
                    "toolCallId": call_id,
                    "result": json.dumps(result_dict)
                }),
            )
        )

    logger.info("Returning %d tool result(s) to Vapi", len(results))
    print(f"Resultt:: {results}")
    return ToolCallResponse(results=results)

# POST /voice/end-of-call

@router.post(
    "/end-of-call",
    status_code=status.HTTP_200_OK,
    summary="Vapi end-of-call webhook",
    description=(
        "Receives the full call transcript and metadata after a call ends. "
        "Persists the transcript linked to the patient record (if registered)."
    ),
)
async def handle_end_of_call(
    request: Request,
    x_vapi_signature: str | None = Header(None, alias="x-vapi-signature"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()

    if not _verify_vapi_signature(raw_body, x_vapi_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    message    = body.get("message", {})
    call_meta  = message.get("call", {})
    artifact   = message.get("artifact", {})
    vapi_call_id = call_meta.get("id") if call_meta else None

    logger.info(
        "End-of-call webhook | call_id=%s | ended_reason=%s | duration=%ss",
        vapi_call_id,
        message.get("endedReason"),
        message.get("durationSeconds"),
    )

    # Pull transcript
    transcript = artifact.get("transcript") if artifact else None

    # We don't have enough context here to know patient_id / completion status
    # without re-parsing the transcript. We store what we have and let the
    # analyst query by vapi_call_id to correlate with tool-call logs.
    service = VoiceAgentService(db)
    caller_phone = (
        call_meta.get("customer", {}).get("number")
        if call_meta else None
    )

    service.save_transcript(
        vapi_call_id=vapi_call_id,
        caller_phone=caller_phone,
        transcript=transcript,
        patient_id=None,       
        registration_completed=False,
        was_returning_caller=False,
        was_update_call=False,
        collected_data=None,
        duration_seconds=message.get("durationSeconds"),
    )

    return {"status": "ok"}