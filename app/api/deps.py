from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.patient_service import PatientService

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

def get_patient_service(db: Session = Depends(get_db)):

    return PatientService(db)