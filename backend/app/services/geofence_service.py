"""
BioAttend Ultimate — Geofencing Service
=======================================
Validates that a check-in location is within an active office geofence zone.
Uses Haversine formula for accurate GPS distance calculation.

If NO zones are configured → check-in is allowed (open mode).
If zones exist → at least one zone must match.
Kiosk devices (bypass_kiosk=True zones) skip the check entirely.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class GeofenceCheckResult:
    allowed: bool
    matched_zone: Optional[str]   # zone name if matched
    distance_m: Optional[float]   # distance to nearest zone center
    reason: str


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in meters between two GPS coordinates."""
    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def check_geofence(
    db,
    client_lat: Optional[float],
    client_lon: Optional[float],
    is_kiosk: bool = False,
) -> GeofenceCheckResult:
    """
    Check if (client_lat, client_lon) is inside any active geofence zone.

    Args:
        db: AsyncSession
        client_lat: GPS latitude from client/browser
        client_lon: GPS longitude from client/browser
        is_kiosk: If True and zone has bypass_kiosk=True → allowed automatically

    Returns:
        GeofenceCheckResult
    """
    from sqlalchemy import select
    from app.models import GeofenceZone

    result = await db.execute(
        select(GeofenceZone).where(GeofenceZone.is_active == True)
    )
    zones = result.scalars().all()

    # No zones configured → open mode (allow all)
    if not zones:
        return GeofenceCheckResult(
            allowed=True,
            matched_zone=None,
            distance_m=None,
            reason="No geofence zones configured — open mode",
        )

    # Kiosk device + kiosk-bypass zone exists → allow
    if is_kiosk and any(z.bypass_kiosk for z in zones):
        return GeofenceCheckResult(
            allowed=True,
            matched_zone="kiosk-bypass",
            distance_m=0.0,
            reason="Kiosk device — geofence bypassed",
        )

    # No GPS coordinates provided → deny if zones exist
    if client_lat is None or client_lon is None:
        return GeofenceCheckResult(
            allowed=False,
            matched_zone=None,
            distance_m=None,
            reason="GPS location required for attendance. Please enable location access.",
        )

    # Check each zone
    nearest_dist = float("inf")
    nearest_zone = None

    for zone in zones:
        dist = _haversine_meters(client_lat, client_lon, zone.latitude, zone.longitude)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest_zone = zone.name
        if dist <= zone.radius_meters:
            return GeofenceCheckResult(
                allowed=True,
                matched_zone=zone.name,
                distance_m=round(dist, 1),
                reason=f"Within {zone.name} ({round(dist)}m from center)",
            )

    return GeofenceCheckResult(
        allowed=False,
        matched_zone=None,
        distance_m=round(nearest_dist, 1),
        reason=(
            f"You are {round(nearest_dist)}m from the nearest office ({nearest_zone}). "
            f"Check-in is only allowed within the designated office area."
        ),
    )
