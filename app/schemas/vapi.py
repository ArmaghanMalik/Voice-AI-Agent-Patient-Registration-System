from typing import Any, Optional
from pydantic import BaseModel, Field

# Tool-call webhook  (Vapi → server)

class ToolCallFunction(BaseModel):
    """The function the LLM wants to invoke."""
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallMessage(BaseModel):
    """Single tool call from the LLM."""
    id: str = ""                          # Vapi's tool-call ID (used in response)
    function: ToolCallFunction


class ToolCallPayload(BaseModel):
    """
    Full payload Vapi sends when the LLM invokes a tool.

    Vapi wraps everything in a 'message' object with type='tool-calls'.
    The actual tool calls are in message.toolCallList.
    """
    message: "ToolCallMessage_Outer"


class ToolCallMessage_Outer(BaseModel):
    type: str                              # "tool-calls"
    toolCallList: list[ToolCallMessage] = Field(default_factory=list)
    call: Optional["CallMetadata"] = None  # contains caller info


class CallMetadata(BaseModel):
    """Metadata about the call — included in most Vapi webhooks."""
    id: Optional[str] = None              # Vapi call ID
    customer: Optional["CustomerInfo"] = None


class CustomerInfo(BaseModel):
    number: Optional[str] = None          # caller's phone number (E.164 format)


ToolCallPayload.model_rebuild()
ToolCallMessage_Outer.model_rebuild()


# Tool-call response  (our server → Vapi)

class ToolCallResult(BaseModel):
    """
    Our response to a single tool call.
    Vapi feeds this back to the LLM as the function result.
    """
    toolCallId: str                        # must match ToolCallMessage.id
    result: str                            # JSON string the LLM sees as function output


class ToolCallResponse(BaseModel):
    """Wrapper Vapi expects around tool call results."""
    results: list[ToolCallResult]


# End-of-call webhook  (Vapi → server)

class EndOfCallArtifact(BaseModel):
    """Transcript and recording artifacts from the completed call."""
    transcript: Optional[str] = None       # full conversation transcript
    recordingUrl: Optional[str] = None
    summary: Optional[str] = None         # Vapi's auto-generated summary


class EndOfCallPayload(BaseModel):
    """
    Payload Vapi sends when a call ends.
    We use this to persist the transcript linked to the patient record.
    """
    message: "EndOfCallMessage"


class EndOfCallMessage(BaseModel):
    type: str                              # "end-of-call-report"
    call: Optional[CallMetadata] = None
    artifact: Optional[EndOfCallArtifact] = None
    durationSeconds: Optional[float] = None
    endedReason: Optional[str] = None     # e.g. "customer-ended-call"


EndOfCallPayload.model_rebuild()