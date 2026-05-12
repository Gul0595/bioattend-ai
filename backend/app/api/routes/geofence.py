"""
BioAttend Ultimate — Geofence Zone Admin Routes
"""
from __future__ import annotations
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminOnly, CurrentUser, HROrAbove
from app.core.database import get_db
from app.models import GeofenceZone

router = APIRouter(prefix="/geofence", tags=["Geofencing"])


class ZoneCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius_meters: int = 100
    bypass_kiosk: bool = True


class ZoneOut(BaseModel):
    id: UUID
    name: str
    latitude: float
    longitude: float
    radius_meters: int
    bypass_kiosk: bool
    is_active: bool
    model_config = {"from_attributes": True}


@router.get("/zones", response_model=List[ZoneOut])
async def list_zones(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
):
    result = await db.execute(select(GeofenceZone).where(GeofenceZone.is_active == True))
    return result.scalars().all()


@router.post("/zones", response_model=ZoneOut, status_code=status.HTTP_201_CREATED)
async def create_zone(
    body: ZoneCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: HROrAbove,
):
    zone = GeofenceZone(**body.model_dump())
    db.add(zone)
    await db.flush()
    await db.refresh(zone)
    return zone


@router.delete("/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    zone_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminOnly,
):
    result = await db.execute(select(GeofenceZone).where(GeofenceZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    zone.is_active = False
    await db.flush()


@router.post("/test", response_model=dict)
async def test_geofence(
    lat: float,
    lon: float,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
):
    """Test if a coordinate is inside any zone. Useful for HR to verify zone setup."""
    from app.services.geofence_service import check_geofence
    result = await check_geofence(db, lat, lon, is_kiosk=False)
    return result.__dict__
