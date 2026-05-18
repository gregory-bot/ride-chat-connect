"""End-to-end booking flow test using the in-process bot engine + SQLite."""
import asyncio
import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_waziride.db")

from app.db import AsyncSessionLocal, init_db  # noqa: E402
from app.bot.engine import handle_message  # noqa: E402


@pytest.mark.asyncio
async def test_full_booking_flow(tmp_path, monkeypatch):
    # Use a temp DB file
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    # Reimport to pick up env
    from importlib import reload
    import app.config as cfg
    reload(cfg)
    import app.db as dbmod
    reload(dbmod)
    from app.db import init_db as _init, AsyncSessionLocal as _SL
    await _init()

    phone = "+254700111222"

    async def say(text, lat=None, lng=None):
        async with _SL() as db:
            r = await handle_message(db, phone=phone, channel="whatsapp", body=text, latitude=lat, longitude=lng)
            return r.text

    assert "Welcome" in await say("hi")
    assert "Pickup" in await say("Westlands, Nairobi")
    r = await say("JKIA, Nairobi")
    assert "Estimated fare" in r
    r = await say("YES")
    assert "confirmed" in r.lower()
    r = await say("status")
    assert "Trip" in r
    r = await say("done")
    assert "completed" in r.lower()
