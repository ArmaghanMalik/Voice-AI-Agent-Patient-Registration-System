from fastapi import FastAPI
from app.api.router import api_router
from app.db.session import engine
from app.db.base import Base

app = FastAPI(
    title="Patient Registrtion Agent",
    version="1.0"
)

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

app.include_router(api_router)

@app.get("\health")
def health():
    return {"status": "Ok"}


