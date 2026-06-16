"""
risk_feed.py
────────────
Fetches live risk data for chokepoints and ports along the route.

Sources:
  1. OpenWeatherMap (free tier, key needed) — weather at each chokepoint
  2. USGS Earthquake Hazards (no key needed) — significant earthquakes
  3. VesselFinder API (credit-based, key needed) — port arrivals & sea distance

VesselFinder free account comes with an API key but no pre-loaded credits.
This module uses two endpoints:
  - ExpectedArrivals  = 5 credits/call  → port congestion at destination
  - Distance          = 1 credit/call   → actual sea routing distance + crossings
Credit usage is tracked in st.session_state and capped per session.

Setup:
  OWM_API_KEY → openweathermap.org/api (free, no credit card)
  MT_API_KEY  → your VesselFinder API key (profile page → API key field)
  USGS        → no key required
"""

import urllib.request
import urllib.error
import urllib.parse
import json
import math
from datetime import datetime
from dataclasses import dataclass, field
import streamlit as st

# ── YOUR API KEYS HERE ───────────────────────────────────────────────────────
OWM_API_KEY = "8e51431f22ada850bcaf74c3b946d71e"   # <-- openweathermap.org/api
MT_API_KEY  = "019ecebf4407717eb9ba9bd483b48e76"     # <-- your VesselFinder API key
# ─────────────────────────────────────────────────────────────────────────────

OWM_BASE   = "https://api.openweathermap.org/data/2.5/weather"
USGS_URL   = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson"
VF_BASE    = "https://api.vesselfinder.com"

CACHE_TTL  = 1800   # 30 minutes in seconds

# VesselFinder credit budget (tracked per session — buy more at api.vesselfinder.com)
VF_SESSION_CREDITS  = 20          # conservative per-session cap
VF_CREDITS_ARRIVALS = 5           # ExpectedArrivals cost
VF_CREDITS_DISTANCE = 1           # Distance cost
MT_MONTHLY_CREDITS  = VF_SESSION_CREDITS   # kept for UI compatibility
MT_SESSION_KEY      = "vf_credits_used"    # st.session_state key


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class WeatherSnapshot:
    condition:      str
    description:    str
    wind_speed_ms:  float
    wind_direction: int
    visibility_km:  float
    temp_c:         float
    fetched_at:     str     # ISO string (cache-safe)


@dataclass
class EarthquakeAlert:
    title:       str
    magnitude:   float
    depth_km:    float
    distance_km: float
    time_utc:    str
    url:         str


@dataclass
class PortTraffic:
    """MarineTraffic data for a port."""
    port_name:           str
    expected_vessels_48h: int          # vessels expected in next 48 hours
    congestion_level:    str           # "low" / "medium" / "high"
    sea_distance_km:     float | None  # actual sea distance origin→destination
    credits_used:        int           # how many MT credits this cost
    fetched_at:          str


@dataclass
class RiskPoint:
    name:             str
    lat:              float
    lon:              float
    weather:          WeatherSnapshot | None = None
    weather_risk:     str = "unknown"
    weather_reason:   str = ""
    earthquakes:      list[EarthquakeAlert] = field(default_factory=list)
    seismic_risk:     str = "low"
    port_traffic:     PortTraffic | None = None  # MarineTraffic data
    overall_risk:     str = "unknown"
    summary:          str = ""
    data_available:   bool = False


# ── Chokepoints ───────────────────────────────────────────────────────────────

CHOKEPOINTS = [
    {"name": "Suez Canal",          "lat": 30.42,  "lon": 32.35},
    {"name": "Strait of Hormuz",    "lat": 26.56,  "lon": 56.25},
    {"name": "Strait of Malacca",   "lat":  2.50,  "lon": 101.30},
    {"name": "Bab el-Mandeb",       "lat": 12.58,  "lon": 43.38},
    {"name": "Panama Canal",        "lat":  9.10,  "lon": -79.68},
    {"name": "Strait of Gibraltar", "lat": 35.97,  "lon": -5.50},
    {"name": "English Channel",     "lat": 51.00,  "lon":  1.40},
    {"name": "Cape of Good Hope",   "lat":-34.36,  "lon": 18.47},
    {"name": "Danish Straits",      "lat": 57.50,  "lon": 10.60},
]

SEA_CHOKEPOINTS = {cp["name"] for cp in CHOKEPOINTS}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a  = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _near_route(cp_lat, cp_lon, route_points, threshold=18) -> bool:
    for lat, lon in route_points[::5]:
        if abs(lat - cp_lat) < threshold and abs(lon - cp_lon) < threshold:
            return True
    return False


def _fetch_json(url: str, timeout: int = 8) -> dict | list | None:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "TransportAdvisor/1.0 (portfolio project)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        # 401 = bad API key (expected during dev), not a network failure
        if e.code in (401, 403):
            return {"_auth_error": e.code}
        return None
    except Exception:
        return None


# ── Weather ───────────────────────────────────────────────────────────────────

def _fetch_weather(lat: float, lon: float) -> WeatherSnapshot | None:
    if not api_key_configured():
        return None
    params = urllib.parse.urlencode({
        "lat": lat, "lon": lon,
        "appid": OWM_API_KEY,
        "units": "metric",
    })
    data = _fetch_json(f"{OWM_BASE}?{params}")
    if not data or "weather" not in data:
        return None
    return WeatherSnapshot(
        condition      = data["weather"][0]["main"],
        description    = data["weather"][0]["description"],
        wind_speed_ms  = data.get("wind", {}).get("speed", 0),
        wind_direction = data.get("wind", {}).get("deg", 0),
        visibility_km  = data.get("visibility", 10000) / 1000,
        temp_c         = data.get("main", {}).get("temp", 0),
        fetched_at     = datetime.utcnow().isoformat(),
    )


def _weather_risk(w: WeatherSnapshot) -> tuple[str, str]:
    if w.condition in {"Thunderstorm", "Tornado"}:
        return "high",   f"{w.condition} — {w.description}"
    if w.wind_speed_ms > 20:
        return "high",   f"Gale-force winds {w.wind_speed_ms:.0f} m/s"
    if w.wind_speed_ms > 13 or w.visibility_km < 1:
        return "medium", f"Strong winds {w.wind_speed_ms:.0f} m/s, vis {w.visibility_km:.1f} km"
    if any(x in w.description.lower() for x in ["heavy", "storm"]):
        return "medium", f"{w.description.title()}"
    if w.condition in {"Rain", "Drizzle", "Snow", "Fog"}:
        return "low",    f"{w.condition} ({w.description})"
    return "low", f"Normal — {w.description}"


# ── Earthquakes (USGS) ───────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_usgs_earthquakes() -> list[dict]:
    """Cached significant earthquakes from the past month."""
    data = _fetch_json(USGS_URL, timeout=10)
    if not data or not isinstance(data, dict):
        return []
    events = []
    for f in data.get("features", []):
        p     = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [None, None, None])
        if coords[0] is None:
            continue
        events.append({
            "title": p.get("title", "Earthquake"),
            "mag":   p.get("mag", 0),
            "depth": coords[2] or 0,
            "lat":   coords[1],
            "lon":   coords[0],
            "time":  datetime.utcfromtimestamp(
                        p.get("time", 0) / 1000
                     ).strftime("%d %b %Y %H:%M UTC"),
            "url":   p.get("url", "https://earthquake.usgs.gov"),
        })
    return events


def _nearby_earthquakes(lat, lon, events, radius_km=600) -> list[EarthquakeAlert]:
    nearby = []
    for e in events:
        dist = _haversine_km(lat, lon, e["lat"], e["lon"])
        if dist <= radius_km:
            nearby.append(EarthquakeAlert(
                title       = e["title"],
                magnitude   = e["mag"],
                depth_km    = e["depth"],
                distance_km = round(dist),
                time_utc    = e["time"],
                url         = e["url"],
            ))
    nearby.sort(key=lambda x: (-x.magnitude, x.distance_km))
    return nearby


def _seismic_risk(eqs: list[EarthquakeAlert]) -> str:
    if not eqs:
        return "low"
    max_mag = max(e.magnitude for e in eqs)
    if max_mag >= 7.0:
        return "high"
    if max_mag >= 6.0:
        return "medium"
    return "low"


# ── VesselFinder ─────────────────────────────────────────────────────────────

def mt_key_configured() -> bool:
    return MT_API_KEY != "YOUR_VESSELFINDER_API_KEY"


def _vf_credits_used() -> int:
    return st.session_state.get(MT_SESSION_KEY, 0)


def _vf_spend(credits: int) -> None:
    st.session_state[MT_SESSION_KEY] = _vf_credits_used() + credits


def _vf_budget_remaining() -> int:
    return max(0, VF_SESSION_CREDITS - _vf_credits_used())


def _vf_can_afford(credits: int) -> bool:
    return mt_key_configured() and _vf_budget_remaining() >= credits


# UN/LOCODE lookup for VesselFinder ExpectedArrivals
# Format: city.lower() → LOCODE (2-letter country + 3-letter port)
PORT_LOCODES: dict[str, str] = {
    "mumbai": "INMAA",        "chennai": "INMAA",
    "nhava sheva": "INNSA",   "kolkata": "INCCU",
    "hamburg": "DEHAM",       "rotterdam": "NLRTM",
    "antwerp": "BEANR",       "felixstowe": "GBFXT",
    "southampton": "GBSOU",   "london": "GBLON",
    "singapore": "SGSIN",     "shanghai": "CNSHA",
    "ningbo": "CNNGB",        "tianjin": "CNTXG",
    "shenzhen": "CNSZX",      "guangzhou": "CNGZU",
    "hong kong": "HKHKG",     "busan": "KRPUS",
    "tokyo": "JPTYO",         "yokohama": "JPYOK",
    "los angeles": "USLAX",   "long beach": "USLGB",
    "new york": "USNYC",      "savannah": "USSAV",
    "seattle": "USSEA",       "houston": "USHOU",
    "sydney": "AUSYD",        "melbourne": "AUMEL",
    "cape town": "ZACPT",     "durban": "ZADUR",
    "dubai": "AEDXB",         "jebel ali": "AEJEA",
    "colombo": "LKCMB",       "karachi": "PKKHC",
    "piraeus": "GRPIR",       "barcelona": "ESBCN",
    "genoa": "ITGOA",         "naples": "ITNAP",
    "gdansk": "PLGDN",        "mombasa": "KEMBA",
    "lagos": "NGLOS",         "casablanca": "MACAS",
    "jakarta": "IDJKT",       "bangkok": "THBKK",
    "manila": "PHMNL",        "ho chi minh city": "VNSGN",
    "kuala lumpur": "MYKUL",  "doha": "QADOH",
}


def _resolve_locode(city: str) -> str | None:
    return PORT_LOCODES.get(city.strip().lower())


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _vf_expected_arrivals(locode: str) -> dict | None:
    """
    VesselFinder ExpectedArrivals — costs 5 credits.
    URL: GET /expectedarrivals?userkey=KEY&locode=SGSIN&interval=1440
    Returns vessel count and top vessel types, or None.
    Cached 30 min to avoid repeat charges.
    """
    if not _vf_can_afford(VF_CREDITS_ARRIVALS):
        return None

    url = (f"{VF_BASE}/expectedarrivals"
           f"?userkey={MT_API_KEY}"
           f"&locode={locode}"
           f"&interval=1440")          # next 24 hours

    data = _fetch_json(url)
    _vf_spend(VF_CREDITS_ARRIVALS)    # charge regardless (API bills on valid request)

    if not data or (isinstance(data, dict) and "_auth_error" in data):
        return None

    vessels = data if isinstance(data, list) else []
    count   = len(vessels)

    # Tally vessel types from AIS.TYPE field
    types: dict[str, int] = {}
    for v in vessels[:30]:
        ais   = v.get("AIS", {})
        vtype = str(ais.get("TYPE", "Unknown"))
        types[vtype] = types.get(vtype, 0) + 1
    top_types = sorted(types.items(), key=lambda x: -x[1])[:3]

    return {
        "locode":       locode,
        "vessel_count": count,
        "top_types":    top_types,
        "fetched_at":   datetime.utcnow().isoformat(),
    }


@st.cache_data(ttl=CACHE_TTL * 12, show_spinner=False)  # 6-hour cache — stable data
def _vf_sea_distance(
    origin_lon: float, origin_lat: float,
    dest_lon: float,   dest_lat: float,
) -> dict | None:
    """
    VesselFinder Distance API — costs 1 credit.
    URL: GET /distance?userkey=KEY&from=lon,lat&to=lon,lat&gateways=suez,panama,malacca
    Returns sea distance in metres + list of crossings.
    """
    if not _vf_can_afford(VF_CREDITS_DISTANCE):
        return None

    url = (f"{VF_BASE}/distance"
           f"?userkey={MT_API_KEY}"
           f"&from={origin_lon},{origin_lat}"
           f"&to={dest_lon},{dest_lat}"
           f"&gateways=suez,panama,malacca,oresund,kiel")

    data = _fetch_json(url)
    _vf_spend(VF_CREDITS_DISTANCE)

    if not data or (isinstance(data, dict) and "_auth_error" in data):
        return None

    props    = data.get("properties", {}) if isinstance(data, dict) else {}
    dist_m   = props.get("Distance", 0)
    crossings = props.get("Crossing", [])

    if not dist_m:
        return None

    dist_km = round(dist_m / 1000)
    dist_nm = round(dist_km / 1.852)

    return {
        "distance_m":   dist_m,
        "distance_km":  dist_km,
        "distance_nm":  dist_nm,
        "crossings":    crossings,   # e.g. ["Suez canal", "Bab-el-Mandab strait"]
        "fetched_at":   datetime.utcnow().isoformat(),
    }


def _congestion_level(vessel_count: int) -> str:
    if vessel_count >= 40: return "high"
    if vessel_count >= 20: return "medium"
    return "low"


def fetch_port_traffic(
    origin_city: str, dest_city: str,
    is_sea: bool,
    origin_coords: tuple | None = None,
    dest_coords:   tuple | None = None,
) -> dict:
    """
    Main VesselFinder entry point — called ONCE per route.
    Fetches expected arrivals at destination + actual sea distance.
    Strictly respects per-session credit budget.

    origin_coords / dest_coords: (lat, lon) tuples from map_view lookup.
    """
    result = {
        "vf_available":      mt_key_configured(),
        "credits_remaining": _vf_budget_remaining(),
        "credits_used":      _vf_credits_used(),
        "dest_arrivals":     None,
        "sea_distance":      None,
        "congestion_level":  None,
        "congestion_risk":   "unknown",
    }

    if not mt_key_configured() or not is_sea:
        return result

    dest_locode = _resolve_locode(dest_city)

    # Expected arrivals at destination port (5 credits)
    if dest_locode and _vf_can_afford(VF_CREDITS_ARRIVALS):
        arrivals = _vf_expected_arrivals(dest_locode)
        if arrivals:
            level = _congestion_level(arrivals["vessel_count"])
            result["dest_arrivals"]   = arrivals
            result["congestion_level"] = level
            result["congestion_risk"]  = level

    # Sea distance via coordinates (1 credit) — more accurate than port-name lookup
    if (origin_coords and dest_coords and _vf_can_afford(VF_CREDITS_DISTANCE)):
        olat, olon = origin_coords
        dlat, dlon = dest_coords
        dist = _vf_sea_distance(olon, olat, dlon, dlat)
        if dist:
            result["sea_distance"] = dist

    result["credits_remaining"] = _vf_budget_remaining()
    result["credits_used"]      = _vf_credits_used()
    return result


# ── Combined risk ─────────────────────────────────────────────────────────────

RISK_RANK = {"high": 2, "medium": 1, "low": 0, "unknown": -1}

def _overall(w_risk: str, s_risk: str, c_risk: str = "low") -> str:
    w = RISK_RANK.get(w_risk, -1)
    s = RISK_RANK.get(s_risk, 0)
    c = RISK_RANK.get(c_risk, 0)
    combined = max(w, s, c)
    if combined < 0:
        return "unknown"
    return ["low", "medium", "high"][combined]


def _summary(rp: RiskPoint) -> str:
    parts = []
    if rp.weather:
        parts.append(f"{rp.weather.condition}, {rp.weather.wind_speed_ms:.0f} m/s wind")
    if rp.earthquakes:
        eq = rp.earthquakes[0]
        parts.append(f"M{eq.magnitude} earthquake {eq.distance_km} km away ({eq.time_utc})")
    if rp.port_traffic and rp.port_traffic.congestion_level != "low":
        parts.append(f"Port congestion: {rp.port_traffic.congestion_level} "
                     f"({rp.port_traffic.expected_vessels_48h} vessels expected 48 h)")
    return " · ".join(parts) if parts else "No disruptions detected"


# ── Main entry ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_route_risk(route_points_json: str, mode: str,
                     origin_city: str = "", dest_city: str = "",
                     origin_coords_json: str = "", dest_coords_json: str = "") -> list[dict]:
    """
    route_points_json   — JSON list of (lat, lon) tuples (great-circle arc)
    mode                — recommended transport mode
    origin_city         — used for VesselFinder LOCODE lookup
    dest_city           — used for VesselFinder LOCODE lookup
    origin_coords_json  — JSON [lat, lon] for Distance API
    dest_coords_json    — JSON [lat, lon] for Distance API

    Returns list of serialisable dicts (one per chokepoint near the route).
    Cached for 30 minutes.
    """
    route_points   = json.loads(route_points_json)
    is_sea         = "Sea" in mode or mode == "Multimodal"
    usgs_events    = _fetch_usgs_earthquakes()

    origin_coords  = tuple(json.loads(origin_coords_json)) if origin_coords_json else None
    dest_coords    = tuple(json.loads(dest_coords_json))   if dest_coords_json   else None

    # VesselFinder — called ONCE per route
    port_data = fetch_port_traffic(
        origin_city, dest_city, is_sea,
        origin_coords=origin_coords,
        dest_coords=dest_coords,
    )

    results = []
    for cp in CHOKEPOINTS:
        if not _near_route(cp["lat"], cp["lon"], route_points):
            continue
        if cp["name"] in SEA_CHOKEPOINTS and not is_sea:
            continue

        rp = RiskPoint(name=cp["name"], lat=cp["lat"], lon=cp["lon"])

        # Weather
        w = _fetch_weather(cp["lat"], cp["lon"])
        if w:
            rp.weather        = w
            rp.weather_risk, rp.weather_reason = _weather_risk(w)
            rp.data_available = True

        # Earthquakes
        rp.earthquakes  = _nearby_earthquakes(cp["lat"], cp["lon"], usgs_events)
        rp.seismic_risk = _seismic_risk(rp.earthquakes)
        if rp.earthquakes:
            rp.data_available = True

        # Port traffic — attach to first chokepoint only (route-level data)
        if not results and port_data.get("dest_arrivals"):
            arrivals = port_data["dest_arrivals"]
            sea_dist = port_data.get("sea_distance")
            rp.port_traffic = PortTraffic(
                port_name            = arrivals.get("locode", dest_city),
                expected_vessels_48h = arrivals["vessel_count"],
                congestion_level     = port_data["congestion_level"],
                sea_distance_km      = sea_dist["distance_km"] if sea_dist else None,
                credits_used         = (VF_CREDITS_ARRIVALS +
                                        (VF_CREDITS_DISTANCE if sea_dist else 0)),
                fetched_at           = arrivals["fetched_at"],
            )
            rp.data_available = True

        c_risk          = port_data.get("congestion_risk", "low") if not results else "low"
        rp.overall_risk = _overall(rp.weather_risk, rp.seismic_risk, c_risk)
        rp.summary      = _summary(rp)
        results.append(_to_dict(rp))

    # If no chokepoints on route, still surface port data
    if not results and port_data.get("dest_arrivals"):
        results.append({"_port_only": True, "port_data": port_data})

    return results


def _to_dict(rp: RiskPoint) -> dict:
    return {
        "name":           rp.name,
        "lat":            rp.lat,
        "lon":            rp.lon,
        "overall_risk":   rp.overall_risk,
        "weather_risk":   rp.weather_risk,
        "weather_reason": rp.weather_reason,
        "seismic_risk":   rp.seismic_risk,
        "summary":        rp.summary,
        "data_available": rp.data_available,
        "weather": {
            "condition":      rp.weather.condition,
            "description":    rp.weather.description,
            "wind_speed_ms":  rp.weather.wind_speed_ms,
            "wind_direction": rp.weather.wind_direction,
            "visibility_km":  rp.weather.visibility_km,
            "temp_c":         rp.weather.temp_c,
            "fetched_at":     rp.weather.fetched_at,
        } if rp.weather else None,
        "earthquakes": [
            {
                "title":       e.title,
                "magnitude":   e.magnitude,
                "depth_km":    e.depth_km,
                "distance_km": e.distance_km,
                "time_utc":    e.time_utc,
                "url":         e.url,
            } for e in rp.earthquakes
        ],
        "port_traffic": {
            "port_name":            rp.port_traffic.port_name,
            "expected_vessels_48h": rp.port_traffic.expected_vessels_48h,
            "congestion_level":     rp.port_traffic.congestion_level,
            "sea_distance_km":      rp.port_traffic.sea_distance_km,
            "credits_used":         rp.port_traffic.credits_used,
            "fetched_at":           rp.port_traffic.fetched_at,
        } if rp.port_traffic else None,
    }


# ── UI helpers ────────────────────────────────────────────────────────────────

RISK_COLOUR = {"low": "#22c55e", "medium": "#f59e0b",
               "high": "#ef4444", "unknown": "#94a3b8"}
RISK_EMOJI  = {"low": "🟢", "medium": "🟡",
               "high": "🔴", "unknown": "⚪"}
RISK_LABEL  = {"low": "Normal", "medium": "Elevated",
               "high": "High risk", "unknown": "No data"}

def api_key_configured() -> bool:
    return OWM_API_KEY != "YOUR_OPENWEATHERMAP_API_KEY"

def mt_key_configured() -> bool:
    return MT_API_KEY != "YOUR_VESSELFINDER_API_KEY"

# Aliases used by app.py (keep names stable across the refactor)
def _mt_budget_remaining() -> int:
    return _vf_budget_remaining()

def _mt_credits_used() -> int:
    return _vf_credits_used()

def wind_dir(deg: int) -> str:
    dirs = ["N","NE","E","SE","S","SW","W","NW"]
    return dirs[round(deg / 45) % 8]
