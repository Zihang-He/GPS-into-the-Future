"""
geo_normalize.py — Minimal, practical MVP for your project

Functions provided:
- normalize(lat, lon, dt_utc, weather, climate=None, heading_deg=None, radius_m=150)
- scene_card(norm)

Internal helpers you can reuse:
- osm_features(lat, lon, r=150)
- tz_for_point(lat, lon)
- to_local(dt_utc, tzname)
- derive_calendar(dt_local, lat, lon)
- sun_position_flags(lat, lon, dt_local)
- lookup_koppen_leafstate(lat, lon, doy)

Dependencies (install with pip):
  pip install osmnx shapely pyproj timezonefinder astral holidays

Notes:
- OSM queries use Overpass via osmnx; keep radius small (≤250m) to be quick.
- If a dependency is missing, functions raise a clear ImportError.
- Weather is passed in by you (since you said it’s given). Example schema below.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from datetime import timezone
from astral import Observer
from astral.sun import azimuth, elevation

# --- Optional heavy deps are imported inside functions so the module loads even if not installed ---

# -----------------------------
# Public API
# -----------------------------

def normalize(
    lat: float,
    lon: float,
    dt_utc: datetime,
    weather: Dict[str, Any],
    climate: Optional[Dict[str, Any]] = None,
    heading_deg: Optional[float] = None,
    radius_m: int = 150,
) -> Dict[str, Any]:
    """Create the canonical, deterministic struct used by your pipeline.

    Parameters
    ----------
    lat, lon : WGS84 coordinates
    dt_utc   : naive or aware UTC datetime (aware preferred)
    weather  : dict like {"label": "overcast", "temp_c": 7.4, "wind_mps": 3.1,
                          "precip_mm": 0.0, "visibility_km": 8.0}
    climate  : optional dict; if None, we guess Koppen + leaf_on via a heuristic
    heading_deg: camera heading if available (0=N, 90=E)
    radius_m: OSM query radius
    """
    place_type, nearest_poi, landuse_counts = osm_features(lat, lon, r=radius_m)

    tzname = tz_for_point(lat, lon)
    dt_local = to_local(dt_utc, tzname)
    cal = derive_calendar(dt_local, lat, lon)

    sun = sun_position_flags(lat, lon, dt_local)

    if climate is None:
        koppen, leaf_on = lookup_koppen_leafstate(lat, lon, cal["doy"])  # simple heuristic
    else:
        koppen = climate.get("koppen", "Cfb")
        leaf_on = climate.get("leaf_on", True)

    norm = {
        "geo": {
            "lat": float(lat),
            "lon": float(lon),
            "nearest_poi": nearest_poi,
            "place_type": place_type,
            "landuse_counts": landuse_counts,
        },
        "time": {
            "dt_utc": dt_utc.replace(tzinfo=None).isoformat() + "Z",
            "dt_local": dt_local.isoformat(),
            "weekday": cal["weekday"],
            "doy": cal["doy"],
            "is_holiday": cal["is_holiday"],
        },
        "sun": sun,
        "weather": weather,
        "climate": {"koppen": koppen, "leaf_on": bool(leaf_on)},
        "camera": {"heading_deg": heading_deg, "hfov_deg": 70},
    }
    return norm


def scene_card(norm: Dict[str, Any]) -> str:
    """Deterministic, CLIP-friendly scene description from normalized struct."""
    landuse = norm["geo"].get("landuse_counts", {})
    landuse_top = ", ".join(sorted(landuse, key=landuse.get, reverse=True)[:3]) or "unknown"
    sun = norm["sun"]
    wx = norm["weather"]
    t = norm["time"]
    c = norm["climate"]

    phase = (
        "golden" if sun.get("is_golden_hour")
        else ("blue" if sun.get("is_blue_hour") else ("day" if sun.get("is_day") else "night"))
    )

    nearest_poi = norm["geo"].get("nearest_poi") or "no notable POI"

    return (
        f'{norm["geo"]["place_type"]} streetscape near {nearest_poi}.\n'
        f'Layout: {landuse_top}. '
        f'Time: {t["dt_local"][11:16]}, sun {sun["azimuth_deg"]:.0f}°/{sun["elevation_deg"]:.0f}° ({phase}). '
        f'Weather: {wx.get("label", "unknown")}, '
        f'{wx.get("temp_c", 0):.0f}°C, wind {wx.get("wind_mps", 0):.0f} m/s, '
        f'visibility {wx.get("visibility_km", 0):.0f} km. '
        f'Season: {"leaf-on" if c.get("leaf_on") else "leaf-off"} ({c.get("koppen", "?")}).'
    )


# -----------------------------
# Helpers (with real implementations)
# -----------------------------

def osm_features(lat: float, lon: float, r: int = 150) -> Tuple[str, Optional[str], Dict[str, int]]:
    """Query OSM around point to get a coarse "place_type", nearest POI name, and land-use counts.

    Strategy:
      - Pull amenities, shops, tourism, leisure to find a nearby named POI.
      - Pull landuse + natural + highway features to build a categorical count vector.
      - Heuristically derive place_type from landuse/highway makeup.
    """
    try:
        import osmnx as ox
        import pandas as pd
    except ImportError as e:
        raise ImportError("osm_features requires 'osmnx' and 'pandas'. Install via pip.") from e

    point = (lat, lon)

    # Query named POIs
    poi_tags = {
        "amenity": True,
        "shop": True,
        "tourism": True,
        "leisure": True,
        "historic": True,
    }
    gdf_poi = ox.features_from_point(point, tags=poi_tags, dist=r)

    nearest_poi = None
    if not gdf_poi.empty:
        for col in ["name", "brand", "operator"]:
            if col in gdf_poi.columns and gdf_poi[col].notna().any():
                nearest_poi = str(gdf_poi[col].dropna().iloc[0])
                break

    # Land use / environment / roads
    land_tags = {
        "landuse": True,
        "natural": True,
        "leisure": True,
        "highway": True,
        "waterway": True,
        "building": True,
        "park": True,
    }
    gdf_land = ox.features_from_point(point, tags=land_tags, dist=r)

    # Count categories
    cats = {
        "residential": 0, "retail": 0, "industrial": 0, "commercial": 0,
        "park": 0, "forest": 0, "water": 0, "farmland": 0,
        "road_major": 0, "road_minor": 0, "building": 0
    }

    if not gdf_land.empty:
        # landuse
        if "landuse" in gdf_land.columns:
            counts = gdf_land["landuse"].fillna("").value_counts()
            for k, v in counts.items():
                k = str(k)
                if k in cats:
                    cats[k] += int(v)
                elif k in ("grass", "meadow", "recreation_ground"):
                    cats["park"] += int(v)
                elif k in ("forest", "wood"):
                    cats["forest"] += int(v)
                elif k in ("farmland", "farm", "orchard", "vineyard"):
                    cats["farmland"] += int(v)
        # natural
        if "natural" in gdf_land.columns:
            counts = gdf_land["natural"].fillna("").value_counts()
            for k, v in counts.items():
                if str(k) in ("water", "wetland"):
                    cats["water"] += int(v)
                if str(k) in ("wood", "forest"):
                    cats["forest"] += int(v)
        # highway (roads)
        if "highway" in gdf_land.columns:
            counts = gdf_land["highway"].fillna("").value_counts()
            for k, v in counts.items():
                k = str(k)
                if k in ("motorway", "trunk", "primary"):
                    cats["road_major"] += int(v)
                elif k in ("secondary", "tertiary", "residential", "service", "unclassified"):
                    cats["road_minor"] += int(v)
        # building
        if "building" in gdf_land.columns:
            cats["building"] += int(gdf_land["building"].notna().sum())

    # Heuristic place type
    def derive_place_type(c: Dict[str, int]) -> str:
        if c["retail"] + c["commercial"] > 5 and c["road_major"] >= 1:
            return "urban_commercial"
        if c["residential"] + c["building"] > 20 and c["road_minor"] > 3:
            return "urban_residential"
        if c["park"] + c["forest"] > 5 and c["building"] < 10:
            return "parkland"
        if c["farmland"] > 3 and c["building"] < 5:
            return "rural_farmland"
        if c["industrial"] > 2:
            return "industrial"
        return "mixed_urban"

    place_type = derive_place_type(cats)

    return place_type, nearest_poi, cats


def tz_for_point(lat: float, lon: float) -> str:
    try:
        from timezonefinder import TimezoneFinder
    except ImportError as e:
        raise ImportError("tz_for_point requires 'timezonefinder'. Install via pip.") from e
    tf = TimezoneFinder()
    tzname = tf.timezone_at(lng=lon, lat=lat)
    if tzname is None:
        tzname = "UTC"
    return tzname


def to_local(dt_utc: datetime, tzname: str) -> datetime:
    """Convert UTC -> local timezone (returns aware datetime)."""
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
    except Exception:
        raise ImportError("Python 3.9+ required for zoneinfo; or install 'pytz' and adapt.")

    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=ZoneInfo("UTC"))
    return dt_utc.astimezone(ZoneInfo(tzname))


def derive_calendar(dt_local: datetime, lat: float, lon: float) -> Dict[str, Any]:
    """Weekday, day-of-year, basic holiday flag (country inferred crudely from lon/lat heuristics)."""
    import math
    weekday = dt_local.strftime("%a")
    doy = int(dt_local.strftime("%j"))

    # crude country inference: use lon to guess EU vs US for demo purposes
    country = "FR" if -10 <= lon <= 30 and 35 <= lat <= 60 else "US"
    try:
        import holidays
        is_holiday = dt_local.date() in holidays.country_holidays(country)
    except Exception:
        is_holiday = False

    return {"weekday": weekday, "doy": doy, "is_holiday": bool(is_holiday)}

def sun_position_flags(lat: float, lon: float, dt_local: datetime) -> Dict[str, Any]:
    """
    dt_local must be timezone-aware (e.g., Europe/Paris).
    Returns azimuth/elevation in degrees plus simple flags.
    """
    if dt_local.tzinfo is None:
        raise ValueError("dt_local must be timezone-aware (has tzinfo).")

    obs = Observer(latitude=lat, longitude=lon)  # altitude defaults to 0
    az = float(azimuth(obs, dt_local))           # degrees, 0°=North, clockwise
    el = float(elevation(obs, dt_local))         # degrees above horizon

    # Simple lighting flags
    is_day = el > 0
    is_blue_hour = -6.0 <= el <= 0.0
    is_golden_hour = 0.0 < el <= 10.0
    is_night = el < -6.0

    return {
        "azimuth_deg": az,
        "elevation_deg": el,
        "is_day": is_day,
        "is_blue_hour": is_blue_hour,
        "is_golden_hour": is_golden_hour,
        "is_night": is_night,
    }

def lookup_koppen_leafstate(lat: float, lon: float, doy: int) -> Tuple[str, bool]:
    """Tiny heuristic fallback for climate class + leaf-on state.
    - Koppen class guessed coarsely from latitude belt.
    - Leaf-on if (late spring .. early fall) in temperate bands.
    Replace with a proper raster lookup later.
    """
    # extremely coarse Koppen guess
    abs_lat = abs(lat)
    if abs_lat < 10:
        koppen = "Af"  # equatorial rainforest
    elif abs_lat < 23:
        koppen = "Aw"  # tropical savanna
    elif abs_lat < 35:
        koppen = "BSh"  # subtropical steppe (very rough)
    elif abs_lat < 55:
        koppen = "Cfb"  # temperate oceanic (rough default for EU)
    else:
        koppen = "Dfb"  # continental

    # leaf-on: May(≈120) to Oct(≈300) for temperate; always true in tropics, false in high lat winter
    if koppen in ("Cfb", "Dfb"):
        leaf_on = 120 <= doy <= 300
    elif koppen in ("Af", "Aw"):
        leaf_on = True
    else:
        leaf_on = 150 <= doy <= 280

    return koppen, bool(leaf_on)


# -----------------------------
# Demo
# -----------------------------
if __name__ == "__main__":
    # Example: Eiffel Tower, Nov 26, 2025 17:00 UTC
    import json
    dt = datetime(2025, 12, 25, 17, 0, 0)  # UTC
    weather = {"label": "overcast", "temp_c": 7.4, "wind_mps": 3.1, "precip_mm": 0.0, "visibility_km": 8.0}

    norm = normalize(48.85837, 2.29448, dt, weather)
    print(json.dumps(norm, indent=2))
    print("\nSCENE CARD:\n", scene_card(norm))
