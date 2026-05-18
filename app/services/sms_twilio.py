"""Outbound messaging via Twilio (used for proactive notifications / testing)."""
from __future__ import annotations

from app.config import settings


def _client():
    from twilio.rest import Client
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_whatsapp(to_phone: str, body: str) -> dict:
    if not settings.TWILIO_ACCOUNT_SID:
        print(f"[Twilio-WA dev] to={to_phone} msg={body!r}")
        return {"status": "skipped"}
    to = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
    msg = _client().messages.create(from_=settings.TWILIO_WHATSAPP_FROM, to=to, body=body)
    return {"sid": msg.sid, "status": msg.status}


def send_sms(to_phone: str, body: str) -> dict:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_SMS_FROM:
        print(f"[Twilio-SMS dev] to={to_phone} msg={body!r}")
        return {"status": "skipped"}
    msg = _client().messages.create(from_=settings.TWILIO_SMS_FROM, to=to_phone, body=body)
    return {"sid": msg.sid, "status": msg.status}
