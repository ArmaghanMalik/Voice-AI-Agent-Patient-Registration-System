import uuid
import enum
from datetime import datetime, date

from sqlalchemy import (
    String,
    Date,
    DateTime,
    Enum as SAEnum,
    func,
    Boolean,
    Index,
)

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base

class SexEnum(str, enum.Enum):
    male = "Male"
    female = "Female"
    other = "Other"
    decline = "Decline to Answer"

class Patient(Base):
    __tablename__ = "patients"

    # primary key
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Required demographic fields
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)

    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)

    sex: Mapped[SexEnum] = mapped_column(
        SAEnum(SexEnum, name="sex_enum"),
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
        index=True,
        )
    
    # Optional info
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    address_line_1: Mapped[str] = mapped_column(String(255), nullable=False) 
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)

    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(10), nullable=False)

    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)

    preferred_language: Mapped[str] = mapped_column(
        String(50),
        default="English",
        nullable=False,
    )

    # Delete
    is_deleted: Mapped[str] = mapped_column(Boolean, default=False, nullable=False)

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    ) 

    # Timestaps
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

Index("idx_patient_last_name", Patient.last_name)
Index("idex_patient_dob", Patient.date_of_birth)