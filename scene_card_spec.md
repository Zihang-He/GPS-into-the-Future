
# Scene Card v0.1 — Machine‑Readable Spec

This document explains every attribute in the **scene card** your pipeline produces.
A *scene card* is a compact, deterministic description of a place, time, and conditions near a GPS point. It is meant to be used as: (1) a generation prompt, (2) a retrieval query, and (3) a record for evaluation/reproducibility.

---

## 1) Top‑level Structure

```json
{
  "version": "0.1",
  "id": "sc_20251009T1320_48.85837_2.29448",
  "source": {
    "gps": {"lat": 48.85837, "lon": 2.29448, "heading_deg": null},
    "datetime_local": "2025-10-09T13:20:00+02:00",
    "timezone": "Europe/Paris"
  },
  "location": {
    "country_code": "FR",
    "region": "Île-de-France",
    "city": "Paris",
    "neighborhood": "Gros-Caillou",
    "display_name": "Gros-Caillou, Paris, Île-de-France, FR"
  },
  "map_context": {
    "landuse": ["residential"],
    "elements": {
      "road_type": "residential",
      "sidewalk": true,
      "water": false,
      "park": false,
      "building_height_hint": "midrise",
      "building_density": "medium",
      "pois": ["cafe","bakery"]
    }
  },
  "sun": {
    "azimuth_deg": 230.0,
    "elevation_deg": 15.0,
    "is_day": true,
    "is_blue_hour": false,
    "is_golden_hour": true,
    "is_night": false
  },
  "weather": {
    "condition": "overcast",
    "temperature_c": 14.2,
    "precip_mm": 0.6,
    "wind_mps": 3.2,
    "wet_ground": true
  },
  "climate": "Cfb",
  "prompt": "Quiet residential street with mid‑rise apartments...",
  "notes": "",
  "provenance": {
    "reverse_geocoder": "nominatim",
    "osm_provider": "overpass",
    "sun_provider": "astral",
    "weather_provider": "open-meteo",
    "created_at_utc": "2025-10-09T11:20:00Z"
  },
  "confidence": {
    "location": 0.98,
    "map_context": 0.75,
    "sun": 0.99,
    "weather": 0.80
  }
}
```

---

## 2) Field‑by‑Field Definitions

### `version` *(string, required)*
Schema version. Bump on breaking changes.

### `id` *(string, recommended)*
Stable, unique identifier you assign (e.g., timestamp + rounded lat/lon). Useful for caching and joins.

### `source` *(object, required)*
Raw inputs used to build the card.
- `gps.lat` *(number, degrees)* — Latitude in WGS‑84.
- `gps.lon` *(number, degrees)* — Longitude in WGS‑84.
- `gps.heading_deg` *(number|null, degrees)* — Optional camera/vehicle heading; `0 = North`, clockwise.
- `datetime_local` *(ISO‑8601 string)* — Local time **with offset** (timezone‑aware).
- `timezone` *(IANA tz string)* — e.g., `"Europe/Paris"`.

### `location` *(object, required)*
Reverse‑geocoded admin labels (used for human readability and coarse conditioning).
- `country_code` *(string, ISO‑3166‑1 alpha‑2)* — e.g., `FR`.
- `region` *(string)* — First‑level admin (state/region).
- `city` *(string)* — City/municipality.
- `neighborhood` *(string)* — Local area name, if available.
- `display_name` *(string)* — Full label from the geocoder (free‑text).

### `map_context` *(object, required)*
Summary of nearby OpenStreetMap features within a small radius (e.g., 100–200 m).
- `landuse` *(array[string])* — Dominant land use tags. Common values: `residential`, `commercial`, `retail`, `industrial`, `forest`, `farmland`, `recreation_ground`, `cemetery`, `military`, `university`, `railway`.
- `elements` *(object)* — Compact, model‑friendly cues:
  - `road_type` *(string)* — Most frequent `highway` class near the point. One of: `motorway`, `trunk`, `primary`, `secondary`, `tertiary`, `residential`, `service`, `track`, `footway`, `cycleway`.
  - `sidewalk` *(boolean)* — True if sidewalks are mapped on nearby ways.
  - `water` *(boolean)* — Any water features (river, lake, canal) within radius.
  - `park` *(boolean)* — Park/green or leisure areas within radius.
  - `building_height_hint` *(string)* — Heuristic bucket from footprints/tags: `lowrise` (1–2), `midrise` (3–6), `highrise` (7+), `unknown`.
  - `building_density` *(string)* — Heuristic: `sparse`, `medium`, `dense`.
  - `pois` *(array[string])* — Short list of notable nearby POI types (e.g., `cafe`, `school`, `parking`, `place_of_worship`).

> **Derivation note:** These are summaries; keep the raw GeoDataFrame separately if you need reproducibility.

### `sun` *(object, required)*
Solar geometry and lighting flags at `datetime_local`.
- `azimuth_deg` *(number, degrees)* — `0 = North`, `90 = East`, clockwise.
- `elevation_deg` *(number, degrees)* — Angle above horizon; negative at night.
- `is_day` *(boolean)* — `elevation_deg > 0`.
- `is_blue_hour` *(boolean)* — `-6 ≤ elevation_deg ≤ 0` (civil twilight).
- `is_golden_hour` *(boolean)* — `0 < elevation_deg ≤ 10` (heuristic).
- `is_night` *(boolean)* — `elevation_deg < -6`.

### `weather` *(object, required)*
Observed/forecast daily conditions for that local date (or nearest).
- `condition` *(string)* — Canonical label such as `clear`, `partly_cloudy`, `overcast`, `light_rain`, `rain`, `snow`, `fog`, `thunderstorm`.
- `temperature_c` *(number|null)* — Near‑surface temperature (°C), if available.
- `precip_mm` *(number|null)* — Accumulated precipitation over the relevant period (mm).
- `wind_mps` *(number|null)* — Wind speed (m/s), if available.
- `wet_ground` *(boolean)* — Heuristic flag derived from `condition` + `precip_mm`.

### `climate` *(string, recommended)*
Köppen–Geiger climate code (e.g., `Cfb`, `BWh`). Use a static raster lookup; optional but useful for style priors.

### `prompt` *(string, required)*
A 1–2 sentence natural‑language description distilled from the card; intended for CLIP retrieval or text‑to‑image prompting. Keep it concise and deterministic (avoid randomness unless you log seeds).

### `notes` *(string, optional)*
Free‑text scratchpad for human comments or pipeline warnings.

### `provenance` *(object, recommended)*
Where each piece came from (for auditing/caching).
- `reverse_geocoder` *(string)* — e.g., `nominatim` (with version if possible).
- `osm_provider` *(string)* — e.g., `overpass`/`osmnx`.
- `sun_provider` *(string)* — e.g., `astral 2.2` or `pvlib 0.10`.
- `weather_provider` *(string)* — e.g., `open-meteo vX.Y` or `NOAA ISD`.
- `created_at_utc` *(ISO‑8601)* — Card creation timestamp.

### `confidence` *(object, optional)*
Per‑section confidence scores in `[0,1]` (heuristic or model‑based).
- `location`, `map_context`, `sun`, `weather` *(number)* — Higher means more reliable.

---

## 3) Conventions & Units

- **Coordinates**: WGS‑84 (`EPSG:4326`), decimal degrees.
- **Angles**: degrees. Azimuth is clockwise from North.
- **Times**: Always include timezone offsets. Store both local and UTC when relevant.
- **Distances**: meters. Radii for OSM queries should be logged with the card (e.g., in `notes` or extend `map_context.radius_m`).

---

## 4) Minimal JSON Schema (informal)

```json
{
  "type": "object",
  "required": ["version","source","location","map_context","sun","weather","prompt"],
  "properties": {
    "version": {"type":"string"},
    "id": {"type":"string"},
    "source": {
      "type":"object",
      "required":["gps","datetime_local","timezone"],
      "properties":{
        "gps":{"type":"object","required":["lat","lon"],"properties":{
          "lat":{"type":"number"},"lon":{"type":"number"},"heading_deg":{"type":["number","null"]}
        }},
        "datetime_local":{"type":"string"},
        "timezone":{"type":"string"}
      }
    }
  }
}
```

(You can codify a full JSON Schema later; this is just a pointer.)

---

## 5) Examples

### Dense urban dusk, light rain
```json
{
  "version":"0.1",
  "source":{"gps":{"lat":40.7580,"lon":-73.9855},"datetime_local":"2025-03-12T18:05:00-05:00","timezone":"America/New_York"},
  "location":{"country_code":"US","region":"NY","city":"New York","neighborhood":"Midtown","display_name":"Midtown, New York, NY, US"},
  "map_context":{"landuse":["commercial"],"elements":{"road_type":"primary","sidewalk":true,"water":false,"park":false,"building_height_hint":"highrise","building_density":"dense","pois":["theatre","restaurant"]}},
  "sun":{"azimuth_deg":255,"elevation_deg":3,"is_day":true,"is_blue_hour":false,"is_golden_hour":true,"is_night":false},
  "weather":{"condition":"light_rain","temperature_c":6.1,"precip_mm":1.2,"wind_mps":5.0,"wet_ground":true},
  "climate":"Dfa",
  "prompt":"Busy commercial avenue with high‑rise towers, bright signage, wet pavement and light rain at dusk.",
  "provenance":{"reverse_geocoder":"nominatim","osm_provider":"overpass","sun_provider":"astral 2.2","weather_provider":"open-meteo","created_at_utc":"2025-03-12T23:05:02Z"}
}
```

---

## 6) Change Log

- **v0.1**: initial draft: clarified OSM summaries, added `confidence`, `provenance`, and units.
