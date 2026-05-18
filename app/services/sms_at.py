"""Outbound SMS via Africa's Talking."""
from __future__ import annotations

from typing import Iterable

from app.config import settings


def send_sms(recipients: Iterable[str], message: str) -> dict:
    if not settings.AT_API_KEY:
        # No-op in dev; print for visibility.
        print(f"[AT-SMS dev] to={list(recipients)} msg={message!r}")
        return {"status": "skipped", "reason": "AT_API_KEY not configured"}
    import africastalking

    africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
    sms = africastalking.SMS
    kwargs = {}
    if settings.AT_SMS_SHORTCODE:
        kwargs["sender_id"] = settings.AT_SMS_SHORTCODE
    return sms.send(message, list(recipients), **kwargs)
