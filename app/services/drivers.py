"""Driver matching. Currently picks the next available driver from the DB.
Seeds a few mock drivers on first call so the system works out of the box.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Driver


SEED_DRIVERS = [
    {"name": "John Mwangi", "phone": "+254700000001", "plate": "KDB 123X", "vehicle": "Toyota Axio White", "rating": 4.9},
    {"name": "Mary Achieng", "phone": "+254700000002", "plate": "KCA 456Y", "vehicle": "Nissan Note Silver", "rating": 4.8},
    {"name": "Peter Otieno", "phone": "+254700000003", "plate": "KDD 789Z", "vehicle": "Mazda Demio Blue", "rating": 4.7},
    {"name": "Grace Wanjiru", "phone": "+254700000004", "plate": "KDE 222A", "vehicle": "Honda Fit Grey", "rating": 4.95},
]


async def ensure_seed(db: AsyncSession) -> None:
    count = (await db.execute(select(Driver))).scalars().first()
    if count is not None:
        return
    for d in SEED_DRIVERS:
        db.add(Driver(**d, available=True))
    await db.commit()


async def find_available(db: AsyncSession) -> Optional[Driver]:
    await ensure_seed(db)
    row = (await db.execute(select(Driver).where(Driver.available == True).limit(1))).scalar_one_or_none()  # noqa: E712
    if row:
        row.available = False
        await db.commit()
        await db.refresh(row)
    return row


async def release(db: AsyncSession, driver_id: int) -> None:
    drv = await db.get(Driver, driver_id)
    if drv:
        drv.available = True
        await db.commit()
