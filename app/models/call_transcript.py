import uuid
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Boolean, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base


class CallTranscript(Base):
    __tablename__ = "call_transcripts"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
)

    # Vapi's own call identifier — lets us correlate our record with Vapi's dashboard
    vapi_call_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True,
        comment="Vapi's call ID from the webhook payload",
    )

    # Foreign key to patient
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("patients.patient_id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)

    # Caller's phone number (from Vapi metadata, before normalisation)
    caller_phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Outcome of the call
    registration_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    was_returning_caller: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    was_update_call: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Full conversation transcript (provided by Vapi in end-of-call webhook)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Summary — the final collected payload logged as JSON text
    # This is the "log agent conversations" requirement 
    collected_data_snapshot: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON snapshot of the patient data the agent collected",
    )

    # Duration in seconds
    call_duration_seconds: Mapped[int | None] = mapped_column(nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )