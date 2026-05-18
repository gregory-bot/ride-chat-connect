"""Twilio WhatsApp webhook. Configure your Twilio Sandbox/number to POST here.

Endpoint: POST /webhooks/twilio/whatsapp
Twilio sends application/x-www-form-urlencoded fields including:
  From=whatsapp:+2547...   Body=...   Latitude=...   Longitude=...
We respond with TwiML <Response><Message>...</Message></Response>.
"""
from __future__ import annotations

from typing import Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.engine import handle_message
from app.db import get_session

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio"])


def _twiml(text: str) -> Response:
    body = f"<?xml version='1.0' encoding='UTF-8'?><Response><Message>{escape(text)}</Message></Response>"
    return Response(content=body, media_type="application/xml")


@router.post("/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(""),
    Latitude: Optional[float] = Form(None),
    Longitude: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_session),
):
    phone = From.replace("whatsapp:", "").strip()
    reply = await handle_message(
        db, phone=phone, channel="whatsapp", body=Body, latitude=Latitude, longitude=Longitude
    )
    return _twiml(reply.text)


@router.post("/sms")
async def twilio_sms_webhook(
    From: str = Form(...),
    Body: str = Form(""),
    db: AsyncSession = Depends(get_session),
):
    reply = await handle_message(db, phone=From.strip(), channel="sms", body=Body)
    return _twiml(reply.text)
