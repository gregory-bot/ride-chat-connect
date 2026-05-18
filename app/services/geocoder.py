"""Geocoding + distance/duration estimation.

Uses Google Maps if GOOGLE_MAPS_API_KEY is configured; otherwise a deterministic
mock that derives lat/lng from the address string so the bot is fully testable
without external services.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import settings


@dataclass
class GeocodeResult:
    address: str
    lat: float
    lng: float


def _mock_point(address: str) -> GeocodeResult:
    h = hashlib.sha256(address.lower().strip().encode()).digest()
    # Nairobi-ish bounding box
    lat = -1.35 + (h[0] / 255.0) * 0.5
    lng = 36.70 + (h[1] / 255.0) * 0.5
    return GeocodeResult(address=address, lat=round(lat, 6), lng=round(lng, 6))


async def geocode(address: str) -> Optional[GeocodeResult]:
    if not address or not address.strip():
        return None
    if not settings.GOOGLE_MAPS_API_KEY:
        return _mock_point(address)
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params={"address": address, "key": settings.GOOGLE_MAPS_API_KEY})
        data = r.json()
    if data.get("status") != "OK" or not data.get("results"):
        return _mock_point(address)
    res = data["results"][0]
    loc = res["geometry"]["location"]
    return GeocodeResult(address=res["formatted_address"], lat=loc["lat"], lng=loc["lng"])


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def estimate_trip(p_lat: float, p_lng: float, d_lat: float, d_lng: float) -> tuple[float, float]:
    """Return (distance_km, duration_min). Assumes ~28 km/h urban average."""
    km = haversine_km(p_lat, p_lng, d_lat, d_lng)
    minutes = (km / 28.0) * 60.0
    return round(km, 2), round(max(minutes, 1.0), 1)
