"""Lightweight admin/inspection endpoints — useful for testing without a frontend."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.engine import handle_message
from app.db import get_session
from app.models.entities import Driver, Trip, User

router = APIRouter(prefix="/admin", tags=["admin"])


class SimulateIn(BaseModel):
    phone: str
    body: str
    channel: str = "whatsapp"
    latitude: float | None = None
    longitude: float | None = None


@router.post("/simulate")
async def simulate(payload: SimulateIn, db: AsyncSession = Depends(get_session)):
    """Send a message to the bot as if it came over WhatsApp/SMS. Returns the bot reply."""
    reply = await handle_message(
        db,
        phone=payload.phone,
        channel=payload.channel,
        body=payload.body,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    return {"reply": reply.text}


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(select(User))).scalars().all()
    return [{"id": u.id, "phone": u.phone, "channel": u.channel} for u in rows]


@router.get("/trips")
async def list_trips(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(select(Trip).order_by(Trip.id.desc()).limit(50))).scalars().all()
    return [
        {
            "id": t.id, "user_id": t.user_id, "driver_id": t.driver_id, "status": t.status,
            "pickup": t.pickup_text, "dropoff": t.dropoff_text,
            "km": t.distance_km, "min": t.duration_min, "fare_kes": t.fare_kes,
        }
        for t in rows
    ]


@router.get("/drivers")
async def list_drivers(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(select(Driver))).scalars().all()
    return [
        {"id": d.id, "name": d.name, "plate": d.plate, "vehicle": d.vehicle,
         "rating": d.rating, "available": d.available, "phone": d.phone}
        for d in rows
    ]
