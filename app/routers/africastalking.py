"""Africa's Talking SMS webhook (Incoming Messages callback URL).

AT posts application/x-www-form-urlencoded with: from, to, text, date, id, linkId.
We reply asynchronously by sending an outbound SMS via the AT API.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.engine import handle_message
from app.db import get_session
from app.services.sms_at import send_sms

router = APIRouter(prefix="/webhooks/africastalking", tags=["africastalking"])


@router.post("/sms")
async def at_incoming_sms(
    background: BackgroundTasks,
    from_: str = Form(..., alias="from"),
    to: str = Form(""),
    text: str = Form(""),
    db: AsyncSession = Depends(get_session),
):
    reply = await handle_message(db, phone=from_.strip(), channel="sms", body=text)
    background.add_task(send_sms, [from_], reply.text)
    return {"ok": True}


@router.post("/delivery")
async def at_delivery_report(
    id: str = Form(""),
    status: str = Form(""),
    phoneNumber: str = Form(""),
):
    # Acknowledge delivery reports
    return {"ok": True, "id": id, "status": status, "phone": phoneNumber}
