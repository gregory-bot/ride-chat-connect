"""Conversation state machine for WhatsApp + SMS ride booking.

States:
  idle            -> greeting, prompts for pickup
  awaiting_pickup -> stores pickup, asks for dropoff
  awaiting_dropoff-> stores dropoff, computes fare estimate, asks for confirmation
  awaiting_confirm-> on YES: assigns driver, moves to in_trip; on NO: back to idle
  in_trip         -> handles STATUS / ARRIVED / DONE / SOS / CANCEL
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Driver, Session, Trip, User
from app.services import drivers as driver_svc
from app.services.geocoder import GeocodeResult, estimate_trip, geocode
from app.services.pricing import compute_fare


@dataclass
class Reply:
    text: str


HELP = (
    "Commands:\n"
    "• HI / START — begin a new booking\n"
    "• STATUS — current trip status\n"
    "• CANCEL — cancel current request\n"
    "• SOS — emergency help\n"
    "• HELP — show this menu"
)


async def _get_or_create_user(db: AsyncSession, phone: str, channel: str) -> User:
    row = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    if row:
        if row.channel != channel:
            row.channel = channel
            await db.commit()
        return row
    user = User(phone=phone, channel=channel)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _get_session(db: AsyncSession, user: User) -> Session:
    row = (await db.execute(select(Session).where(Session.user_id == user.id))).scalar_one_or_none()
    if row:
        return row
    s = Session(user_id=user.id, state="idle", data="{}")
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _set_state(db: AsyncSession, sess: Session, state: str, data: Optional[dict] = None) -> None:
    sess.state = state
    if data is not None:
        sess.data = json.dumps(data)
    await db.commit()


async def _active_trip(db: AsyncSession, user: User) -> Optional[Trip]:
    row = (
        await db.execute(
            select(Trip).where(Trip.user_id == user.id, Trip.status.in_(["requested", "matched", "arrived", "in_progress"]))
            .order_by(Trip.id.desc()).limit(1)
        )
    ).scalar_one_or_none()
    return row


def _parse_latlng(text: str) -> Optional[tuple[float, float]]:
    """Accept 'lat,lng' such as '-1.2921,36.8219'."""
    try:
        a, b = text.split(",", 1)
        lat = float(a.strip())
        lng = float(b.strip())
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng
    except Exception:
        return None
    return None


async def _resolve_location(text: str) -> Optional[GeocodeResult]:
    ll = _parse_latlng(text)
    if ll:
        return GeocodeResult(address=f"({ll[0]:.5f}, {ll[1]:.5f})", lat=ll[0], lng=ll[1])
    return await geocode(text)


async def handle_message(
    db: AsyncSession,
    *,
    phone: str,
    channel: str,
    body: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Reply:
    body_raw = (body or "").strip()
    body = body_raw.lower()
    user = await _get_or_create_user(db, phone, channel)
    sess = await _get_session(db, user)

    # Global commands
    if body in {"help", "menu", "?"}:
        return Reply(HELP)

    if body == "sos":
        trip = await _active_trip(db, user)
        ctx = f" Trip #{trip.id}, driver: {trip.driver_id}." if trip else ""
        return Reply(
            "🆘 SOS received. Our safety team has been notified."
            + ctx
            + " If life is in danger, call 999 immediately."
        )

    if body == "cancel":
        trip = await _active_trip(db, user)
        if not trip:
            await _set_state(db, sess, "idle", {})
            return Reply("Nothing to cancel. Send HI to start a new booking.")
        trip.status = "cancelled"
        if trip.driver_id:
            await driver_svc.release(db, trip.driver_id)
        await db.commit()
        await _set_state(db, sess, "idle", {})
        return Reply(f"❌ Trip #{trip.id} cancelled. Send HI to book another ride.")

    if body == "status":
        trip = await _active_trip(db, user)
        if not trip:
            return Reply("You have no active trip. Send HI to book a ride.")
        drv = await db.get(Driver, trip.driver_id) if trip.driver_id else None
        msg = (
            f"📋 Trip #{trip.id} — {trip.status.upper()}\n"
            f"From: {trip.pickup_text}\nTo: {trip.dropoff_text}\n"
            f"Fare: KES {trip.fare_kes:.0f} • {trip.distance_km} km • ~{trip.duration_min:.0f} min"
        )
        if drv:
            msg += f"\nDriver: {drv.name} ({drv.plate}) ⭐ {drv.rating}\nCall: {drv.phone}"
        return Reply(msg)

    # State transitions
    if body in {"hi", "hello", "start", "hey", "habari"} or sess.state == "idle":
        if body in {"hi", "hello", "start", "hey", "habari"}:
            await _set_state(db, sess, "awaiting_pickup", {})
            return Reply(
                "👋 Welcome to WaziRide!\n"
                "Where should we pick you up?\n"
                "Reply with an address (e.g. 'Westlands, Nairobi') or share a location pin.\n"
                "You can also send 'lat,lng' like -1.2921,36.8219"
            )

    if sess.state == "awaiting_pickup":
        if latitude is not None and longitude is not None:
            loc = GeocodeResult(address=body_raw or f"({latitude:.5f},{longitude:.5f})", lat=latitude, lng=longitude)
        else:
            loc = await _resolve_location(body_raw)
        if not loc:
            return Reply("Sorry, I couldn't find that location. Please send a clearer address.")
        await _set_state(db, sess, "awaiting_dropoff", {
            "pickup": {"text": loc.address, "lat": loc.lat, "lng": loc.lng}
        })
        return Reply(f"📍 Pickup: {loc.address}\n\nWhere to? Reply with the destination address.")

    if sess.state == "awaiting_dropoff":
        loc = await _resolve_location(body_raw)
        if not loc:
            return Reply("Sorry, I couldn't find that destination. Try again with a clearer address.")
        data = json.loads(sess.data or "{}")
        p = data.get("pickup")
        if not p:
            await _set_state(db, sess, "idle", {})
            return Reply("Something went wrong. Send HI to start again.")
        km, mins = estimate_trip(p["lat"], p["lng"], loc.lat, loc.lng)
        fare = compute_fare(km, mins)
        data["dropoff"] = {"text": loc.address, "lat": loc.lat, "lng": loc.lng}
        data["estimate"] = {"km": km, "min": mins, "fare": fare}
        await _set_state(db, sess, "awaiting_confirm", data)
        return Reply(
            f"📍 From: {p['text']}\n📍 To: {loc.address}\n"
            f"🚗 ~{km} km • ~{mins:.0f} min\n"
            f"💰 Estimated fare: KES {fare:.0f}\n\n"
            f"Reply YES to confirm, NO to cancel."
        )

    if sess.state == "awaiting_confirm":
        if body in {"yes", "y", "confirm", "ok"}:
            data = json.loads(sess.data or "{}")
            p, d, est = data.get("pickup"), data.get("dropoff"), data.get("estimate")
            if not (p and d and est):
                await _set_state(db, sess, "idle", {})
                return Reply("Something went wrong. Send HI to start again.")
            trip = Trip(
                user_id=user.id,
                pickup_text=p["text"], pickup_lat=p["lat"], pickup_lng=p["lng"],
                dropoff_text=d["text"], dropoff_lat=d["lat"], dropoff_lng=d["lng"],
                distance_km=est["km"], duration_min=est["min"], fare_kes=est["fare"],
                status="requested",
            )
            db.add(trip)
            await db.commit()
            await db.refresh(trip)

            drv = await driver_svc.find_available(db)
            if not drv:
                trip.status = "cancelled"
                await db.commit()
                await _set_state(db, sess, "idle", {})
                return Reply("Sorry, no drivers available right now. Please try again shortly.")
            trip.driver_id = drv.id
            trip.status = "matched"
            await db.commit()

            await _set_state(db, sess, "in_trip", {"trip_id": trip.id})
            return Reply(
                f"✅ Trip #{trip.id} confirmed!\n"
                f"🚗 Driver: {drv.name} ({drv.plate})\n"
                f"🚙 {drv.vehicle} • ⭐ {drv.rating}\n"
                f"📞 {drv.phone}\n"
                f"💰 Fare: KES {trip.fare_kes:.0f}\n\n"
                f"Reply STATUS for updates, CANCEL to cancel, SOS for emergency."
            )
        if body in {"no", "n", "cancel"}:
            await _set_state(db, sess, "idle", {})
            return Reply("Okay, booking cancelled. Send HI to start over.")
        return Reply("Please reply YES to confirm or NO to cancel.")

    if sess.state == "in_trip":
        trip = await _active_trip(db, user)
        if not trip:
            await _set_state(db, sess, "idle", {})
            return Reply("Your trip has ended. Send HI to book another ride.")
        if body in {"arrived", "picked", "start"}:
            trip.status = "in_progress"
            await db.commit()
            return Reply("🚦 Trip started. Safe journey!")
        if body in {"done", "complete", "completed", "finish"}:
            trip.status = "completed"
            trip.completed_at = datetime.utcnow()
            if trip.driver_id:
                await driver_svc.release(db, trip.driver_id)
            await db.commit()
            await _set_state(db, sess, "idle", {})
            return Reply(
                f"🏁 Trip #{trip.id} completed. Fare: KES {trip.fare_kes:.0f}.\n"
                f"Thanks for riding with WaziRide! Reply HI for another trip."
            )
        return Reply("You're on a trip. Reply STATUS, ARRIVED, DONE, CANCEL or SOS.")

    # Fallback
    await _set_state(db, sess, "idle", {})
    return Reply("I didn't catch that. Send HI to start a booking, or HELP for commands.")
