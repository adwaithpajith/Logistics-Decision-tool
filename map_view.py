"""
map_view.py
───────────
Builds a Folium map showing:
  • Origin and destination markers
  • A great-circle arc for the recommended mode
  • Dashed arcs for eligible alternatives
  • Chokepoint markers along sea routes
  • A clean legend

Uses a built-in coordinate lookup (no external geocoding API needed).
"""

import math
import folium
import streamlit as st

# ── Built-in coordinate lookup ───────────────────────────────────────────────
# (city.lower() -> (lat, lon))  — covers major logistics hubs

CITY_COORDS: dict[str, tuple[float, float]] = {
    # India
    "mumbai": (19.08, 72.88), "chennai": (13.08, 80.27),
    "delhi": (28.61, 77.21), "new delhi": (28.61, 77.21),
    "kolkata": (22.57, 88.36), "bangalore": (12.97, 77.59),
    "bengaluru": (12.97, 77.59), "hyderabad": (17.38, 78.47),
    "nhava sheva": (18.95, 72.95), "cochin": (9.93, 76.26),
    "kochi": (9.93, 76.26), "ahmedabad": (23.03, 72.58),
    # Germany
    "hamburg": (53.55, 9.99), "berlin": (52.52, 13.40),
    "frankfurt": (50.11, 8.68), "munich": (48.14, 11.58),
    "bremen": (53.08, 8.80), "düsseldorf": (51.23, 6.79),
    "cologne": (50.94, 6.96), "stuttgart": (48.78, 9.18),
    # China
    "shanghai": (31.23, 121.47), "beijing": (39.91, 116.39),
    "shenzhen": (22.54, 114.06), "guangzhou": (23.13, 113.26),
    "tianjin": (39.14, 117.18), "ningbo": (29.87, 121.54),
    "qingdao": (36.07, 120.38), "hong kong": (22.32, 114.17),
    # USA
    "new york": (40.71, -74.01), "los angeles": (34.05, -118.24),
    "chicago": (41.88, -87.63), "houston": (29.76, -95.37),
    "miami": (25.77, -80.19), "seattle": (47.61, -122.33),
    "long beach": (33.77, -118.19), "savannah": (32.08, -81.10),
    # UK
    "london": (51.51, -0.13), "felixstowe": (51.96, 1.35),
    "southampton": (50.90, -1.40), "birmingham": (52.48, -1.90),
    "manchester": (53.48, -2.24), "bristol": (51.45, -2.59),
    # Singapore / SE Asia
    "singapore": (1.35, 103.82), "kuala lumpur": (3.14, 101.69),
    "bangkok": (13.75, 100.52), "ho chi minh city": (10.82, 106.63),
    "jakarta": (-6.21, 106.85), "manila": (14.60, 120.98),
    "yangon": (16.87, 96.19),
    # Middle East
    "dubai": (25.20, 55.27), "abu dhabi": (24.47, 54.37),
    "jebel ali": (24.98, 55.07), "doha": (25.29, 51.53),
    "riyadh": (24.69, 46.72), "jeddah": (21.49, 39.19),
    "kuwait city": (29.37, 47.98),
    # Australia
    "sydney": (-33.87, 151.21), "melbourne": (-37.81, 144.96),
    "brisbane": (-27.47, 153.02), "perth": (-31.95, 115.86),
    "adelaide": (-34.93, 138.60),
    # Africa
    "cape town": (-33.93, 18.42), "johannesburg": (-26.20, 28.04),
    "durban": (-29.86, 31.02), "nairobi": (-1.29, 36.82),
    "lagos": (6.45, 3.40), "accra": (5.56, -0.20),
    "cairo": (30.06, 31.25), "casablanca": (33.59, -7.62),
    "mombasa": (-4.05, 39.67),
    # Europe
    "rotterdam": (51.92, 4.48), "antwerp": (51.22, 4.40),
    "amsterdam": (52.37, 4.90), "paris": (48.85, 2.35),
    "marseille": (43.30, 5.37), "barcelona": (41.39, 2.15),
    "madrid": (40.42, -3.70), "milan": (45.46, 9.19),
    "rome": (41.90, 12.50), "naples": (40.85, 14.27),
    "athens": (37.98, 23.73), "istanbul": (41.01, 28.95),
    "gdansk": (54.35, 18.65), "piraeus": (37.94, 23.65),
    "valencia": (39.47, -0.38), "genoa": (44.41, 8.93),
    "warsaw": (52.23, 21.01), "vienna": (48.21, 16.37),
    "zurich": (47.38, 8.54), "brussels": (50.85, 4.35),
    "stockholm": (59.33, 18.07), "oslo": (59.91, 10.75),
    "helsinki": (60.17, 24.94), "copenhagen": (55.68, 12.57),
    # Americas
    "toronto": (43.65, -79.38), "vancouver": (49.25, -123.12),
    "montreal": (45.51, -73.56), "buenos aires": (-34.60, -58.38),
    "sao paulo": (-23.55, -46.63), "rio de janeiro": (-22.91, -43.17),
    "santiago": (-33.46, -70.65), "lima": (-12.05, -77.04),
    "bogota": (4.71, -74.07), "mexico city": (19.43, -99.13),
    "panama city": (8.99, -79.52), "manzanillo": (19.05, -104.32),
    # Japan / Korea
    "tokyo": (35.68, 139.69), "osaka": (34.69, 135.50),
    "yokohama": (35.44, 139.64), "nagoya": (35.18, 136.91),
    "seoul": (37.57, 126.98), "busan": (35.18, 129.08),
    "incheon": (37.46, 126.71),
    # South Asia
    "karachi": (24.86, 67.01), "colombo": (6.93, 79.85),
    "dhaka": (23.81, 90.41), "chittagong": (22.34, 91.83),
    "islamabad": (33.72, 73.06),
    # Russia / Central Asia
    "moscow": (55.75, 37.62), "st. petersburg": (59.95, 30.32),
    "vladivostok": (43.12, 131.89), "novosibirsk": (54.99, 82.90),
}

# Country capitals / major ports as fallback
COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "india": (20.59, 78.96), "germany": (51.17, 10.45),
    "china": (35.86, 104.20), "united states": (37.09, -95.71),
    "united kingdom": (55.38, -3.44), "singapore": (1.35, 103.82),
    "australia": (-25.27, 133.78), "japan": (36.20, 138.25),
    "south korea": (35.91, 127.77), "france": (46.23, 2.21),
    "netherlands": (52.13, 5.29), "brazil": (-14.24, -51.93),
    "canada": (56.13, -106.35), "russia": (61.52, 105.32),
    "south africa": (-30.56, 22.94), "uae": (23.42, 53.85),
    "saudi arabia": (23.89, 45.08), "turkey": (38.96, 35.24),
    "indonesia": (-0.79, 113.92), "malaysia": (4.21, 101.98),
    "thailand": (15.87, 100.99), "vietnam": (14.06, 108.28),
    "mexico": (23.63, -102.55), "argentina": (-38.42, -63.62),
    "nigeria": (9.08, 8.68), "kenya": (-0.02, 37.91),
    "egypt": (26.82, 30.80), "pakistan": (30.38, 69.35),
    "bangladesh": (23.68, 90.36), "sri lanka": (7.87, 80.77),
    "norway": (60.47, 8.47), "sweden": (60.13, 18.64),
    "finland": (61.92, 25.75), "denmark": (56.26, 9.50),
    "poland": (51.92, 19.14), "spain": (40.46, -3.75),
    "italy": (41.87, 12.57), "belgium": (50.50, 4.47),
    "switzerland": (46.82, 8.23), "austria": (47.52, 14.55),
    "greece": (39.07, 21.82), "portugal": (39.40, -8.22),
    "ghana": (7.95, -1.02), "ethiopia": (9.15, 40.49),
    "morocco": (31.79, -7.09), "algeria": (28.03, 1.66),
    "iraq": (33.22, 43.68), "iran": (32.43, 53.69),
    "qatar": (25.35, 51.18), "kuwait": (29.31, 47.48),
    "colombia": (4.57, -74.30), "peru": (-9.19, -75.02),
    "chile": (-35.68, -71.54), "taiwan": (23.70, 120.96),
    "philippines": (12.88, 121.77), "cambodia": (12.57, 104.99),
    "myanmar": (19.15, 96.74), "ukraine": (48.38, 31.17),
    "israel": (31.05, 34.85), "jordan": (30.59, 36.24),
    "hungary": (47.16, 19.50), "czech republic": (49.82, 15.47),
    "romania": (45.94, 24.97), "croatia": (45.10, 15.20),
    "new zealand": (-40.90, 174.89), "afghanistan": (33.94, 67.71),
    "uganda": (1.37, 32.29), "zimbabwe": (-19.02, 29.15),
    "yemen": (15.55, 48.52),
}


def lookup_coords(city: str, country: str) -> tuple[float, float] | None:
    c = city.strip().lower()
    if c and c in CITY_COORDS:
        return CITY_COORDS[c]
    # Try country fallback
    cc = country.strip().lower()
    if cc in COUNTRY_COORDS:
        return COUNTRY_COORDS[cc]
    return None


# ── Great-circle interpolation ───────────────────────────────────────────────

def _to_rad(deg): return deg * math.pi / 180
def _to_deg(rad): return rad * 180 / math.pi

def great_circle_points(lat1, lon1, lat2, lon2, n=80):
    φ1, λ1 = _to_rad(lat1), _to_rad(lon1)
    φ2, λ2 = _to_rad(lat2), _to_rad(lon2)
    x1 = math.cos(φ1)*math.cos(λ1); y1 = math.cos(φ1)*math.sin(λ1); z1 = math.sin(φ1)
    x2 = math.cos(φ2)*math.cos(λ2); y2 = math.cos(φ2)*math.sin(λ2); z2 = math.sin(φ2)
    dot = max(-1.0, min(1.0, x1*x2 + y1*y2 + z1*z2))
    omega = math.acos(dot)
    pts = []
    for i in range(n + 1):
        t = i / n
        if omega < 1e-10:
            x, y, z = x1, y1, z1
        else:
            s = math.sin(omega)
            a = math.sin((1-t)*omega)/s; b = math.sin(t*omega)/s
            x = a*x1+b*x2; y = a*y1+b*y2; z = a*z1+b*z2
        lat = _to_deg(math.atan2(z, math.sqrt(x*x+y*y)))
        lon = _to_deg(math.atan2(y, x))
        pts.append((lat, lon))
    return pts


# ── Chokepoints ───────────────────────────────────────────────────────────────

CHOKEPOINTS = [
    {"name": "Suez Canal",          "lat": 30.42,  "lon": 32.35,  "risk": "medium"},
    {"name": "Strait of Hormuz",    "lat": 26.56,  "lon": 56.25,  "risk": "high"},
    {"name": "Strait of Malacca",   "lat":  2.50,  "lon": 101.30, "risk": "medium"},
    {"name": "Bab el-Mandeb",       "lat": 12.58,  "lon": 43.38,  "risk": "high"},
    {"name": "Panama Canal",        "lat":  9.10,  "lon": -79.68, "risk": "low"},
    {"name": "Strait of Gibraltar", "lat": 35.97,  "lon": -5.50,  "risk": "low"},
    {"name": "English Channel",     "lat": 51.00,  "lon":  1.40,  "risk": "low"},
    {"name": "Cape of Good Hope",   "lat":-34.36,  "lon": 18.47,  "risk": "low"},
    {"name": "Danish Straits",      "lat": 57.50,  "lon": 10.60,  "risk": "low"},
]
RISK_COLOUR = {"low": "#22c55e", "medium": "#f59e0b", "high": "#ef4444"}

def _near_route(cp_lat, cp_lon, points, threshold=18):
    for lat, lon in points[::5]:
        if abs(lat - cp_lat) < threshold and abs(lon - cp_lon) < threshold:
            return True
    return False

def _is_sea_mode(mode):
    return "Sea" in mode or mode == "Multimodal"

# ── Mode visuals ──────────────────────────────────────────────────────────────

MODE_STYLE = {
    "Air freight":        {"color": "#6366f1", "dash": None,     "weight": 3, "icon": "✈"},
    "Sea freight (FCL)":  {"color": "#0ea5e9", "dash": "8 6",    "weight": 3, "icon": "🚢"},
    "Sea freight (LCL)":  {"color": "#38bdf8", "dash": "5 5",    "weight": 2, "icon": "🚢"},
    "Road freight":       {"color": "#f97316", "dash": None,     "weight": 3, "icon": "🚛"},
    "Rail freight":       {"color": "#a855f7", "dash": "12 4",   "weight": 3, "icon": "🚂"},
    "Multimodal":         {"color": "#10b981", "dash": "6 3 2 3","weight": 3, "icon": "🔀"},
}


# ── Main builder ──────────────────────────────────────────────────────────────

def build_map(payload: dict, results: list) -> str | None:
    r   = payload.get("route", {})
    p   = payload.get("product", {})
    origin_city    = r.get("origin", {}).get("city", "")
    origin_country = r.get("origin", {}).get("country", "")
    dest_city      = r.get("destination", {}).get("city", "")
    dest_country   = r.get("destination", {}).get("country", "")

    origin_coords = lookup_coords(origin_city, origin_country)
    dest_coords   = lookup_coords(dest_city,   dest_country)

    if not origin_coords or not dest_coords:
        return None

    olat, olon = origin_coords
    dlat, dlon = dest_coords

    m = folium.Map(
        location=[(olat+dlat)/2, (olon+dlon)/2],
        zoom_start=3,
        tiles="CartoDB positron",
        prefer_canvas=True,
    )

    eligible = [res for res in results if res.eligible]
    if not eligible:
        return None

    best = eligible[0]

    # ── Arcs ──────────────────────────────────────────────────────────────────
    for i, res in enumerate(eligible):
        style  = MODE_STYLE.get(res.mode, {"color":"#888","dash":"4 4","weight":2,"icon":"?"})
        points = great_circle_points(olat, olon, dlat, dlon, n=100)
        is_best = (i == 0)

        folium.PolyLine(
            locations=points,
            color=style["color"],
            weight=style["weight"] + (1 if is_best else -1),
            opacity=1.0 if is_best else 0.40,
            dash_array=style["dash"],
            tooltip=(f"{res.mode}  |  score {res.score:.0f}/100  |  "
                     f"{res.estimated_days[0]}–{res.estimated_days[1]} days  |  "
                     f"${res.estimated_cost_usd[0]:,}–${res.estimated_cost_usd[1]:,}"),
        ).add_to(m)

        # Mid-arc badge for best mode only
        if is_best:
            mid = points[len(points)//2]
            folium.Marker(
                location=mid,
                icon=folium.DivIcon(
                    html=f"""<div style="background:{style['color']};color:#fff;
                        padding:4px 10px;border-radius:99px;font-size:12px;
                        font-weight:600;white-space:nowrap;
                        box-shadow:0 2px 6px rgba(0,0,0,0.3);">
                        {style['icon']} {res.mode}</div>""",
                    icon_size=(190, 28), icon_anchor=(95, 14),
                ),
            ).add_to(m)

    # ── Chokepoints for sea / multimodal ──────────────────────────────────────
    if _is_sea_mode(best.mode):
        pts = great_circle_points(olat, olon, dlat, dlon, n=100)
        for cp in CHOKEPOINTS:
            if _near_route(cp["lat"], cp["lon"], pts):
                col = RISK_COLOUR[cp["risk"]]
                folium.CircleMarker(
                    location=[cp["lat"], cp["lon"]],
                    radius=7, color=col, fill=True,
                    fill_color=col, fill_opacity=0.9,
                    tooltip=f"⚠ {cp['name']} — risk: {cp['risk']}",
                ).add_to(m)
                folium.Marker(
                    location=[cp["lat"], cp["lon"]],
                    icon=folium.DivIcon(
                        html=(f'<div style="font-size:11px;color:{col};font-weight:600;'
                              f'white-space:nowrap;margin-top:-16px;margin-left:11px;">'
                              f'{cp["name"]}</div>'),
                        icon_size=(160, 18), icon_anchor=(0, 9),
                    ),
                ).add_to(m)

    # ── Origin marker ─────────────────────────────────────────────────────────
    folium.Marker(
        location=[olat, olon],
        tooltip=f"Origin: {origin_city}, {origin_country}",
        icon=folium.DivIcon(
            html=f"""<div style="background:#1e293b;color:#fff;
                padding:5px 12px;border-radius:8px;font-size:12px;
                font-weight:600;white-space:nowrap;
                box-shadow:0 2px 8px rgba(0,0,0,0.3);">
                📍 {origin_city or origin_country}</div>""",
            icon_size=(200, 30), icon_anchor=(10, 30),
        ),
    ).add_to(m)

    # ── Destination marker ────────────────────────────────────────────────────
    folium.Marker(
        location=[dlat, dlon],
        tooltip=f"Destination: {dest_city}, {dest_country}",
        icon=folium.DivIcon(
            html=f"""<div style="background:#0f172a;color:#f8fafc;
                padding:5px 12px;border-radius:8px;font-size:12px;
                font-weight:600;white-space:nowrap;
                border:2px solid #38bdf8;
                box-shadow:0 2px 8px rgba(0,0,0,0.3);">
                🏁 {dest_city or dest_country}</div>""",
            icon_size=(200, 30), icon_anchor=(10, 30),
        ),
    ).add_to(m)

    # ── Legend ────────────────────────────────────────────────────────────────
    rows = ""
    for res in eligible:
        style  = MODE_STYLE.get(res.mode, {"color":"#888","icon":"?"})
        border = "2px solid #1d4ed8" if res == best else "1px solid #e2e8f0"
        bg     = "#eff6ff" if res == best else "#fff"
        fw     = "600" if res == best else "400"
        rows += f"""
        <div style="display:flex;align-items:center;gap:8px;
                    padding:5px 8px;border-radius:6px;border:{border};
                    margin-bottom:4px;background:{bg};">
          <span style="display:inline-block;width:24px;height:4px;
                       background:{style['color']};border-radius:2px;"></span>
          <span style="font-size:12px;font-weight:{fw};color:#1e293b;">
                {style['icon']} {res.mode}</span>
          <span style="font-size:11px;color:#64748b;margin-left:auto;">
                {res.score:.0f}/100</span>
        </div>"""

    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:12px;z-index:1000;
                background:rgba(255,255,255,0.97);padding:12px 14px;
                border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,0.15);
                min-width:210px;
                font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
      <div style="font-size:12px;font-weight:700;color:#0f172a;margin-bottom:8px;">
          Transport modes</div>
      {rows}
      <div style="font-size:11px;color:#94a3b8;margin-top:6px;">Hover arcs for details</div>
    </div>"""

    m.get_root().html.add_child(folium.Element(legend_html))
    return m._repr_html_()
