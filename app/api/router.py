from fastapi import APIRouter
from app.api import patients
from app.api import voice

api_router = APIRouter()

api_router.include_router(patients.router)
api_router.include_router(voice.router)
