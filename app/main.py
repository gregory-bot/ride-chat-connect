from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import admin, africastalking, whatsapp


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="WaziRide Bot Backend", version="0.1.0", lifespan=lifespan)


@app.get("/")
def root():
    return {
        "name": "WaziRide",
        "status": "ok",
        "docs": "/docs",
        "webhooks": {
            "twilio_whatsapp": "POST /webhooks/twilio/whatsapp",
            "twilio_sms": "POST /webhooks/twilio/sms",
            "africastalking_sms": "POST /webhooks/africastalking/sms",
        },
    }


@app.get("/healthz")
def healthz():
    return {"ok": True}


app.include_router(whatsapp.router)
app.include_router(africastalking.router)
app.include_router(admin.router)
