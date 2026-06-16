import streamlit as st
import json

st.set_page_config(
    page_title="Transport Advisor",
    page_icon="🚚",
    layout="wide",
)

# ── Minimal custom CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
.section-header {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 4px;
    margin-top: 8px;
}
.pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 99px;
    font-size: 12px;
    font-weight: 500;
    margin: 2px 3px 2px 0;
}
.pill-hazmat  { background:#FEE2E2; color:#991B1B; }
.pill-temp    { background:#DBEAFE; color:#1E40AF; }
.pill-fragile { background:#FEF3C7; color:#92400E; }
.pill-bulk    { background:#D1FAE5; color:#065F46; }
.pill-highval { background:#EDE9FE; color:#4C1D95; }
.divider { border:none; border-top:1px solid #e5e7eb; margin: 20px 0 16px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar branding ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚚 Transport Advisor")
    st.markdown("Fill in the three sections to get a transport recommendation.")
    st.markdown("---")
    st.markdown("**Sections**")
    st.markdown("1. 📦 Product profile")
    st.markdown("2. 🗺️ Route profile")
    st.markdown("3. ⚙️ Constraints")
    st.markdown("---")
    st.caption("v0.1 · Input form")

# ── Page title ──────────────────────────────────────────────────────────────
st.title("Shipment Input")
st.caption("Tell us about what you're shipping, where it's going, and your priorities.")

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — PRODUCT PROFILE
# ════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='section-header'>📦 Product profile</div>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    product_category = st.selectbox(
        "Product category",
        options=[
            "General cargo",
            "Perishable goods (food/pharma)",
            "Hazardous materials",
            "Live animals",
            "Oversized / heavy machinery",
            "High-value goods (electronics/jewellery)",
            "Bulk commodities (grain/coal/ore)",
            "Liquid bulk (chemicals/fuel)",
            "Garments & textiles",
            "Automotive parts",
            "Medical / pharmaceutical",
            "E-commerce parcels",
        ],
        help="Broad category drives which modes are even eligible."
    )

    product_name = st.text_input(
        "Describe the product",
        placeholder="e.g. Frozen salmon fillets, 2000 units",
        help="Freetext — used for context in the recommendation."
    )

with col2:
    weight_kg = st.number_input(
        "Total weight (kg)",
        min_value=0.1,
        max_value=500_000.0,
        value=500.0,
        step=10.0,
        format="%.1f"
    )

    volume_m3 = st.number_input(
        "Total volume (m³)",
        min_value=0.01,
        max_value=10_000.0,
        value=2.0,
        step=0.1,
        format="%.2f"
    )

# Special handling flags
st.markdown("**Special handling requirements**")
flag_cols = st.columns(5)
with flag_cols[0]:
    flag_hazmat   = st.checkbox("☢️ Hazardous", help="Includes chemicals, flammables, explosives (ADR/IATA DG rules apply)")
with flag_cols[1]:
    flag_temp     = st.checkbox("❄️ Temperature-controlled", help="Cold chain required — refrigerated or frozen")
with flag_cols[2]:
    flag_fragile  = st.checkbox("🔮 Fragile", help="Requires special packing and handling")
with flag_cols[3]:
    flag_bulk     = st.checkbox("⚓ Bulk / unpacked", help="No individual packaging — poured or piped")
with flag_cols[4]:
    flag_highval  = st.checkbox("💎 High-value", help="Requires insurance, secure handling, possibly armoured transport")

# Temperature range (only shown if temp-controlled)
if flag_temp:
    temp_col1, temp_col2 = st.columns(2)
    with temp_col1:
        temp_min = st.number_input("Min temperature (°C)", value=-18, min_value=-40, max_value=25)
    with temp_col2:
        temp_max = st.number_input("Max temperature (°C)", value=4, min_value=-40, max_value=25)
else:
    temp_min, temp_max = None, None

# Declared value
declared_value_usd = st.number_input(
    "Declared value (USD)",
    min_value=0,
    max_value=10_000_000,
    value=5000,
    step=500,
    help="Used to calculate insurance costs and flag high-value thresholds."
)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ROUTE PROFILE
# ════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='section-header'>🗺️ Route profile</div>", unsafe_allow_html=True)

COUNTRIES = [
    "Afghanistan", "Algeria", "Argentina", "Australia", "Austria",
    "Bangladesh", "Belgium", "Brazil", "Cambodia", "Canada",
    "Chile", "China", "Colombia", "Croatia", "Czech Republic",
    "Denmark", "Egypt", "Ethiopia", "Finland", "France",
    "Germany", "Ghana", "Greece", "Hong Kong", "Hungary",
    "India", "Indonesia", "Iran", "Iraq", "Ireland",
    "Israel", "Italy", "Japan", "Jordan", "Kenya",
    "Malaysia", "Mexico", "Morocco", "Myanmar", "Netherlands",
    "New Zealand", "Nigeria", "Norway", "Pakistan", "Peru",
    "Philippines", "Poland", "Portugal", "Qatar", "Romania",
    "Russia", "Saudi Arabia", "Singapore", "South Africa", "South Korea",
    "Spain", "Sri Lanka", "Sweden", "Switzerland", "Taiwan",
    "Thailand", "Turkey", "UAE", "Uganda", "Ukraine",
    "United Kingdom", "United States", "Vietnam", "Yemen", "Zimbabwe",
]

rcol1, rcol2 = st.columns(2)

with rcol1:
    origin_country = st.selectbox("Origin country", options=COUNTRIES, index=COUNTRIES.index("India"))
    origin_city    = st.text_input("Origin city / port", placeholder="e.g. Chennai")

with rcol2:
    dest_country = st.selectbox("Destination country", options=COUNTRIES, index=COUNTRIES.index("Germany"))
    dest_city    = st.text_input("Destination city / port", placeholder="e.g. Hamburg")

# Infrastructure available at destination
st.markdown("**Infrastructure available at destination**")
infra_cols = st.columns(4)
with infra_cols[0]:
    infra_sea  = st.checkbox("🚢 Seaport", value=True)
with infra_cols[1]:
    infra_air  = st.checkbox("✈️ Airport", value=True)
with infra_cols[2]:
    infra_rail = st.checkbox("🚂 Rail terminal", value=False)
with infra_cols[3]:
    infra_road = st.checkbox("🛣️ Road access", value=True)

distance_km = st.slider(
    "Approximate distance (km)",
    min_value=50,
    max_value=25_000,
    value=7500,
    step=50,
    help="Straight-line distance. The engine will adjust for routing."
)

# Infer distance band
if distance_km < 500:
    dist_band = "Local (< 500 km)"
elif distance_km < 3000:
    dist_band = "Regional (500 – 3,000 km)"
elif distance_km < 8000:
    dist_band = "Long-haul (3,000 – 8,000 km)"
else:
    dist_band = "Intercontinental (> 8,000 km)"

st.caption(f"Distance band: **{dist_band}**")

border_crossings = st.number_input(
    "Number of border crossings",
    min_value=0,
    max_value=20,
    value=1,
    help="More crossings = more customs complexity and delay risk."
)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CONSTRAINTS
# ════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='section-header'>⚙️ Constraints & priorities</div>", unsafe_allow_html=True)

ccol1, ccol2 = st.columns(2)

with ccol1:
    urgency = st.select_slider(
        "Urgency",
        options=["Not urgent (30+ days fine)", "Standard (10–20 days)", "Urgent (3–7 days)", "Critical (next day / same day)"],
        value="Standard (10–20 days)",
        help="Drives whether air freight is worth its premium."
    )

    budget_usd = st.number_input(
        "Max freight budget (USD)",
        min_value=0,
        max_value=500_000,
        value=2000,
        step=100,
        help="Leave at 0 if budget is not a constraint."
    )

with ccol2:
    carbon_priority = st.select_slider(
        "Carbon footprint priority",
        options=["Not a concern", "Nice to minimise", "Important", "Critical — lowest emissions only"],
        value="Nice to minimise",
    )

    reliability = st.select_slider(
        "Schedule reliability priority",
        options=["Flexible", "Moderate", "High", "Mission-critical"],
        value="Moderate",
    )

preferred_modes = st.multiselect(
    "Preferred modes (optional — leave blank to let the engine decide)",
    options=["Air freight", "Sea freight (FCL)", "Sea freight (LCL)", "Road freight", "Rail freight", "Multimodal"],
    help="If you have a preference or contract, select here. Otherwise leave blank."
)

excluded_modes = st.multiselect(
    "Excluded modes",
    options=["Air freight", "Sea freight (FCL)", "Sea freight (LCL)", "Road freight", "Rail freight"],
    help="Modes you cannot or will not use for this shipment."
)

special_notes = st.text_area(
    "Any additional notes",
    placeholder="e.g. Customer requires delivery by a specific date, goods are politically sensitive, carrier preference...",
    height=80,
)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# PAYLOAD PREVIEW + SUBMIT
# ════════════════════════════════════════════════════════════════════════════

# Build the payload dict
flags = []
if flag_hazmat:  flags.append("hazmat")
if flag_temp:    flags.append("temperature_controlled")
if flag_fragile: flags.append("fragile")
if flag_bulk:    flags.append("bulk")
if flag_highval: flags.append("high_value")

infra = []
if infra_sea:  infra.append("sea")
if infra_air:  infra.append("air")
if infra_rail: infra.append("rail")
if infra_road: infra.append("road")

payload = {
    "product": {
        "category":       product_category,
        "description":    product_name,
        "weight_kg":      weight_kg,
        "volume_m3":      volume_m3,
        "flags":          flags,
        "declared_value_usd": declared_value_usd,
        **({"temp_range_c": [temp_min, temp_max]} if flag_temp else {}),
    },
    "route": {
        "origin":         {"country": origin_country, "city": origin_city},
        "destination":    {"country": dest_country,   "city": dest_city},
        "distance_km":    distance_km,
        "distance_band":  dist_band,
        "border_crossings": border_crossings,
        "infra_available": infra,
    },
    "constraints": {
        "urgency":            urgency,
        "budget_usd":         budget_usd,
        "carbon_priority":    carbon_priority,
        "reliability":        reliability,
        "preferred_modes":    preferred_modes,
        "excluded_modes":     excluded_modes,
        "notes":              special_notes,
    }
}

# Summary chips
st.markdown("**Shipment summary**")
chip_parts = [
    f"`{product_category}`",
    f"`{weight_kg:.0f} kg`",
    f"`{distance_km:,} km`",
    f"`{origin_country} → {dest_country}`",
    f"`{urgency}`",
]
if flags:
    chip_parts += [f"`⚠ {f.replace('_',' ')}`" for f in flags]
st.markdown("  ".join(chip_parts))

# Payload preview (collapsible)
with st.expander("View raw payload (JSON)", expanded=False):
    st.json(payload)

st.markdown("")

# Submit button
submitted = st.button("🔍  Get transport recommendation →", type="primary", use_container_width=True)

if submitted:
    # Validation
    errors = []
    if not product_name.strip():
        errors.append("Please describe the product.")
    if not origin_city.strip():
        errors.append("Please enter an origin city.")
    if not dest_city.strip():
        errors.append("Please enter a destination city.")
    if origin_country == dest_country and origin_city.strip() == dest_city.strip():
        errors.append("Origin and destination appear to be the same location.")
    if set(preferred_modes) & set(excluded_modes):
        errors.append("A mode cannot be both preferred and excluded.")
    if not infra:
        errors.append("Please select at least one infrastructure type available at the destination.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        st.success("✅ Input captured. Decision engine will go here in the next step.")
        st.session_state["payload"] = payload
        # Next: pass payload to decision_engine.py


# ════════════════════════════════════════════════════════════════════════════
# DEPARTURE TIME INPUT  (shown always, above results)
# ════════════════════════════════════════════════════════════════════════════

st.markdown("<hr class='divider'>", unsafe_allow_html=True)
st.markdown("<div class='section-header'>🕐 Departure & arrival prediction</div>", unsafe_allow_html=True)

from datetime import datetime, date, timedelta

dcol1, dcol2 = st.columns(2)
with dcol1:
    departure_date = st.date_input(
        "Planned departure date",
        value=date.today() + timedelta(days=3),
        min_value=date.today(),
        help="Date cargo leaves the origin warehouse or is handed to the carrier.",
    )
with dcol2:
    departure_time = st.time_input(
        "Departure time (local)",
        value=datetime.strptime("09:00", "%H:%M").time(),
        help="Used to check cargo cut-off deadlines.",
    )

departure_dt = datetime.combine(departure_date, departure_time)

# ════════════════════════════════════════════════════════════════════════════
# RESULTS
# ════════════════════════════════════════════════════════════════════════════

if submitted and not errors:
    import streamlit.components.v1 as components
    from engine                import evaluate
    from map_view              import build_map, great_circle_points
    from co2_chart             import build_co2_chart, co2_context
    from handling_instructions import get_instructions, get_section_title
    from arrival_predictor     import predict_arrival
    from risk_feed             import (fetch_route_risk, fetch_port_traffic,
                                       api_key_configured, mt_key_configured,
                                       RISK_COLOUR, RISK_EMOJI, RISK_LABEL,
                                       wind_dir, _mt_budget_remaining,
                                       _mt_credits_used, MT_MONTHLY_CREDITS)
    import json

    results  = evaluate(payload)
    eligible = [r for r in results if r.eligible]
    blocked  = [r for r in results if not r.eligible]

    st.markdown("---")
    st.markdown("## 🔍 Recommendation")

    if not eligible:
        st.error("No transport mode is feasible. Try relaxing urgency, "
                 "budget, or infrastructure constraints.")
    else:
        best = eligible[0]

        pred = predict_arrival(
            departure_dt     = departure_dt,
            mode             = best.mode,
            origin_country   = payload["route"]["origin"]["country"],
            dest_country     = payload["route"]["destination"]["country"],
            border_crossings = payload["route"]["border_crossings"],
            transit_days_min = best.estimated_days[0],
            transit_days_max = best.estimated_days[1],
        )

        MODE_COL = {
            "Air freight": "#6366f1", "Sea freight (FCL)": "#0ea5e9",
            "Sea freight (LCL)": "#38bdf8", "Road freight": "#f97316",
            "Rail freight": "#a855f7", "Multimodal": "#10b981",
        }
        col      = MODE_COL.get(best.mode, "#334155")
        CONF_COL = {"High": "#16a34a", "Medium": "#d97706", "Low": "#dc2626"}
        conf_col = CONF_COL.get(pred.confidence, "#64748b")

        # ── Recommendation card ──────────────────────────────────────────────
        st.markdown(f"""
        <div style="border-left:5px solid {col};padding:14px 18px;
                    background:#f8fafc;border-radius:8px;margin-bottom:16px;">
            <div style="font-size:13px;color:#64748b;font-weight:500;
                        text-transform:uppercase;letter-spacing:.06em;">Recommended</div>
            <div style="font-size:22px;font-weight:700;color:#0f172a;margin:4px 0;">
                {best.mode}</div>
            <div style="font-size:13px;color:#475569;">
                Score <strong>{best.score:.0f}/100</strong> &nbsp;·&nbsp;
                {best.estimated_days[0]}–{best.estimated_days[1]} days &nbsp;·&nbsp;
                ${best.estimated_cost_usd[0]:,}–${best.estimated_cost_usd[1]:,} &nbsp;·&nbsp;
                {best.co2_kg:,.1f} kg CO₂ &nbsp;·&nbsp;
                <span style="color:{conf_col};font-weight:600;">
                    ETA {pred.arrival_realistic.strftime('%d %b %Y')}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if pred.missed_cutoff:
            st.warning(f"⚠️ Departure pushed to **{pred.effective_departure.strftime('%A, %d %b %Y')}** "
                       f"(weekend / public holiday).")

        # ── Tabs ─────────────────────────────────────────────────────────────
        tab_risk, tab_arrival, tab_map, tab_co2, tab_handling, tab_why = st.tabs([
            "🛰️ Live risk",
            "🕐 Arrival prediction",
            "🗺️ Route map",
            "🌿 CO₂ comparison",
            "📦 Handling instructions",
            "💡 Why this mode?",
        ])

        # ════════════════════════════════════════════════════════════════════
        # TAB 1 — LIVE RISK
        # ════════════════════════════════════════════════════════════════════
        with tab_risk:
            # Build great-circle arc for chokepoint proximity check
            from map_view import lookup_coords
            o = payload["route"]["origin"]
            d = payload["route"]["destination"]
            oc = lookup_coords(o.get("city",""), o.get("country",""))
            dc = lookup_coords(d.get("city",""), d.get("country",""))

            if not api_key_configured():
                st.info(
                    "**OpenWeatherMap key not configured.**  \n"
                    "Weather data is unavailable until you add your API key to `risk_feed.py`.  \n"
                    "Get a free key at [openweathermap.org/api](https://openweathermap.org/api) "
                    "— 1,000 calls/day, no credit card.  \n\n"
                    "Earthquake data from USGS loads automatically (no key needed)."
                )

            if oc and dc:
                arc_pts = great_circle_points(oc[0], oc[1], dc[0], dc[1], n=100)
                arc_json = json.dumps(arc_pts)

                with st.spinner("Fetching live risk data…"):
                    risk_points = fetch_route_risk(
                        arc_json, best.mode,
                        origin_city        = o.get("city", ""),
                        dest_city          = d.get("city", ""),
                        origin_coords_json = json.dumps(list(oc)),
                        dest_coords_json   = json.dumps(list(dc)),
                    )

                if not risk_points:
                    st.info("No major chokepoints detected along this route, "
                            "or route is too short for chokepoint analysis.")
                else:
                    # Overall route risk banner
                    risk_levels = [rp["overall_risk"] for rp in risk_points
                                   if rp["overall_risk"] != "unknown"]
                    RANK = {"high": 2, "medium": 1, "low": 0}
                    if risk_levels:
                        worst = max(risk_levels, key=lambda x: RANK.get(x, 0))
                        banner_col = RISK_COLOUR[worst]
                        st.markdown(f"""
                        <div style="background:{banner_col}22;border:1px solid {banner_col};
                                    border-radius:8px;padding:12px 16px;margin-bottom:16px;">
                            <span style="font-size:15px;font-weight:700;color:{banner_col};">
                                {RISK_EMOJI[worst]} Route risk: {RISK_LABEL[worst].upper()}
                            </span>
                            <span style="font-size:13px;color:#475569;margin-left:12px;">
                                {len(risk_points)} chokepoint(s) monitored along this route
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

                    # Per-chokepoint cards
                    for rp in risk_points:
                        risk     = rp["overall_risk"]
                        r_col    = RISK_COLOUR.get(risk, "#94a3b8")
                        r_emoji  = RISK_EMOJI.get(risk, "⚪")
                        r_label  = RISK_LABEL.get(risk, "Unknown")

                        with st.expander(
                            f"{r_emoji} **{rp['name']}** — {r_label}",
                            expanded=(risk in ("high", "medium"))
                        ):
                            rc1, rc2 = st.columns(2)

                            # Weather column
                            with rc1:
                                st.markdown("**🌤 Weather**")
                                if rp.get("weather"):
                                    w = rp["weather"]
                                    w_risk = rp["weather_risk"]
                                    w_col  = RISK_COLOUR.get(w_risk, "#94a3b8")
                                    st.markdown(f"""
                                    <div style="background:#f8fafc;border-radius:6px;
                                                padding:10px 12px;font-size:13px;">
                                        <div style="font-weight:600;color:{w_col};">
                                            {RISK_EMOJI.get(w_risk,'⚪')} {w['condition']}
                                        </div>
                                        <div style="color:#475569;margin-top:4px;">
                                            {w['description'].title()}<br>
                                            🌡 {w['temp_c']:.1f}°C &nbsp;
                                            💨 {w['wind_speed_ms']:.1f} m/s {wind_dir(w['wind_direction'])}<br>
                                            👁 Visibility {w['visibility_km']:.1f} km<br>
                                            <span style="font-size:11px;color:#94a3b8;">
                                                Updated {w['fetched_at'][:16].replace('T',' ')} UTC
                                            </span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    if rp["weather_reason"]:
                                        st.caption(f"Risk reason: {rp['weather_reason']}")
                                else:
                                    if api_key_configured():
                                        st.caption("Weather data unavailable (API error).")
                                    else:
                                        st.caption("Add OWM API key to enable weather data.")

                            # Seismic column
                            with rc2:
                                st.markdown("**🌍 Recent earthquakes (USGS)**")
                                eqs = rp.get("earthquakes", [])
                                if eqs:
                                    s_risk = rp["seismic_risk"]
                                    s_col  = RISK_COLOUR.get(s_risk, "#94a3b8")
                                    for eq in eqs[:3]:
                                        st.markdown(f"""
                                        <div style="background:#f8fafc;border-radius:6px;
                                                    padding:8px 12px;font-size:13px;
                                                    margin-bottom:6px;
                                                    border-left:3px solid {s_col};">
                                            <strong>M{eq['magnitude']}</strong>
                                            &nbsp;·&nbsp; {eq['distance_km']} km away<br>
                                            <span style="color:#475569;font-size:12px;">
                                                {eq['title']}<br>
                                                Depth {eq['depth_km']:.0f} km
                                                &nbsp;·&nbsp; {eq['time_utc']}
                                            </span>
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.markdown("""
                                    <div style="background:#f0fdf4;border-radius:6px;
                                                padding:10px 12px;font-size:13px;color:#166534;">
                                        🟢 No significant earthquakes recorded near this
                                        chokepoint in the past month.
                                    </div>
                                    """, unsafe_allow_html=True)

                    # ── VesselFinder port traffic card ─────────────────────
                    is_sea_mode = "Sea" in best.mode or best.mode == "Multimodal"
                    if is_sea_mode:
                        st.markdown("---")
                        st.markdown("#### 🚢 Port traffic (VesselFinder)")

                        if not mt_key_configured():
                            st.info(
                                "**VesselFinder key not configured.**  \n"
                                "Paste your API key into `risk_feed.py` (MT_API_KEY).  \n"
                                "Your key is on your VesselFinder account page under **API key**.  \n"
                                "Note: ExpectedArrivals costs 5 credits/call · Distance costs 1 credit/call."
                            )
                        else:
                            # Credit budget meter
                            used      = _mt_credits_used()
                            remaining = _mt_budget_remaining()
                            pct       = int((used / MT_MONTHLY_CREDITS) * 100)
                            bar_col   = "#ef4444" if pct > 80 else "#f59e0b" if pct > 50 else "#22c55e"
                            st.markdown(f"""
                            <div style="background:#f8fafc;border:1px solid #e2e8f0;
                                        border-radius:8px;padding:10px 14px;margin-bottom:12px;">
                                <div style="font-size:12px;font-weight:600;color:#475569;
                                            margin-bottom:6px;">
                                    VesselFinder — session credit budget
                                </div>
                                <div style="background:#e2e8f0;border-radius:99px;height:8px;
                                            overflow:hidden;">
                                    <div style="background:{bar_col};width:{pct}%;
                                                height:8px;border-radius:99px;
                                                transition:width 0.3s;"></div>
                                </div>
                                <div style="font-size:12px;color:#64748b;margin-top:4px;">
                                    {used} / {MT_MONTHLY_CREDITS} credits used this session
                                    &nbsp;·&nbsp; {remaining} remaining
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # Find port_traffic data from risk_points
                            pt = next(
                                (rp.get("port_traffic") for rp in risk_points
                                 if rp.get("port_traffic")),
                                None
                            )

                            if pt:
                                c_level = pt["congestion_level"]
                                c_col   = RISK_COLOUR.get(c_level, "#94a3b8")
                                c_emoji = RISK_EMOJI.get(c_level, "⚪")

                                ptc1, ptc2 = st.columns(2)
                                with ptc1:
                                    st.markdown(f"""
                                    <div style="background:#f8fafc;border-radius:8px;
                                                padding:12px 14px;border-left:4px solid {c_col};">
                                        <div style="font-size:12px;color:#64748b;
                                                    font-weight:500;text-transform:uppercase;
                                                    letter-spacing:.05em;">
                                            Destination port congestion
                                        </div>
                                        <div style="font-size:18px;font-weight:700;
                                                    color:{c_col};margin:4px 0;">
                                            {c_emoji} {c_level.title()}
                                        </div>
                                        <div style="font-size:13px;color:#475569;">
                                            <strong>{pt['expected_vessels_48h']}</strong>
                                            vessels expected at {pt['port_name']} in next 48 h
                                        </div>
                                        <div style="font-size:11px;color:#94a3b8;margin-top:4px;">
                                            Updated {pt['fetched_at'][:16].replace('T',' ')} UTC
                                            · cost {pt['credits_used']} credits
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)

                                with ptc2:
                                    if pt.get("sea_distance_km"):
                                        dist_km   = pt["sea_distance_km"]
                                        dist_nm   = round(dist_km / 1.852)
                                        # Find crossings from port_data in risk_points
                                        crossings = []
                                        for rp2 in risk_points:
                                            pd2 = rp2.get("port_data", {})
                                            sd2 = pd2.get("sea_distance", {})
                                            if sd2 and sd2.get("crossings"):
                                                crossings = sd2["crossings"]
                                                break
                                        crossing_str = (", ".join(crossings[:4])
                                                        if crossings else "Direct route")
                                        st.markdown(f"""
                                        <div style="background:#f8fafc;border-radius:8px;
                                                    padding:12px 14px;border-left:4px solid #0ea5e9;">
                                            <div style="font-size:12px;color:#64748b;
                                                        font-weight:500;text-transform:uppercase;
                                                        letter-spacing:.05em;">
                                                Actual sea distance
                                            </div>
                                            <div style="font-size:18px;font-weight:700;
                                                        color:#0ea5e9;margin:4px 0;">
                                                {dist_km:,} km
                                            </div>
                                            <div style="font-size:13px;color:#475569;">
                                                {dist_nm:,} nautical miles
                                                · Route via: {crossing_str}
                                            </div>
                                            <div style="font-size:11px;color:#94a3b8;
                                                        margin-top:4px;">
                                                vs {payload['route']['distance_km']:,} km
                                                straight-line estimate
                                                · VesselFinder Distance API
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        st.caption("Sea distance unavailable — "
                                                   "coordinates not resolved or credits exhausted.")
                            else:
                                st.caption(
                                    "Port traffic data unavailable — destination port not "
                                    "recognised or credits exhausted for this session."
                                )

                    # Data freshness note
                    st.caption(
                        "🛰️ Weather: OpenWeatherMap (live) · "
                        "Earthquakes: USGS Significant Earthquakes past 30 days · "
                        "Port traffic: VesselFinder API · "
                        "Data cached 30 minutes"
                    )

            else:
                st.info("Enter a valid origin and destination city to see live risk data.")

        # ════════════════════════════════════════════════════════════════════
        # TAB 2 — ARRIVAL PREDICTION
        # ════════════════════════════════════════════════════════════════════
        with tab_arrival:
            am1, am2, am3, am4 = st.columns(4)
            with am1:
                st.metric("Earliest arrival",
                          pred.arrival_optimistic.strftime("%d %b %Y"))
            with am2:
                st.metric("Realistic arrival",
                          pred.arrival_realistic.strftime("%d %b %Y"),
                          delta=f"+{(pred.arrival_realistic-pred.arrival_optimistic).days}d vs best",
                          delta_color="off")
            with am3:
                st.metric("Latest arrival",
                          pred.arrival_conservative.strftime("%d %b %Y"),
                          delta=f"+{(pred.arrival_conservative-pred.arrival_optimistic).days}d vs best",
                          delta_color="off")
            with am4:
                st.metric("Confidence", pred.confidence)

            st.markdown(f"""
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
                        padding:10px 14px;margin:8px 0 16px;font-size:13px;color:#475569;">
                <strong style="color:{conf_col};">● {pred.confidence} confidence</strong>
                &nbsp;— {pred.confidence_reason}
            </div>
            """, unsafe_allow_html=True)

            st.info(
                f"**Cargo cut-off:** {pred.cutoff_deadline.strftime('%A, %d %b %Y at %H:%M')}  "
                f"({best.mode} requires cargo at terminal "
                f"{int((departure_dt - pred.cutoff_deadline).total_seconds()/3600):.0f} hrs before departure)"
            )

            if pred.origin_holidays_hit:
                names = ", ".join(f"{d.strftime('%d %b')} ({n})"
                                  for d, n in pred.origin_holidays_hit[:3])
                st.warning(f"📅 Holidays at **origin** near departure: {names}")
            if pred.dest_holidays_hit:
                names = ", ".join(f"{d.strftime('%d %b')} ({n})"
                                  for d, n in pred.dest_holidays_hit[:3])
                st.warning(f"📅 Holidays at **destination** during arrival window: {names}")

            st.markdown("#### Journey timeline")
            for i, step in enumerate(pred.timeline):
                is_last = (i == len(pred.timeline) - 1)
                bg  = "#f0fdf4" if is_last else "#f8fafc"
                bdr = "#86efac" if is_last else "#e2e8f0"
                st.markdown(f"""
                <div style="display:flex;gap:14px;align-items:flex-start;
                            margin-bottom:8px;padding:10px 14px;
                            background:{bg};border:1px solid {bdr};border-radius:8px;">
                    <div style="min-width:120px;font-size:12px;font-weight:600;
                                color:#1e293b;padding-top:2px;">
                        {step['date'].strftime('%a, %d %b')}
                    </div>
                    <div>
                        <div style="font-size:13px;font-weight:600;color:#0f172a;">
                            {step['label']}</div>
                        <div style="font-size:12px;color:#64748b;margin-top:2px;">
                            {step['note']}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

            st.markdown("#### Time breakdown")
            bc1, bc2 = st.columns(2)
            with bc1:
                st.markdown(f"""
                | Component | Days |
                |---|---|
                | Transit (min–max) | {pred.transit_days_min}–{pred.transit_days_max} |
                | Border delays (×{payload['route']['border_crossings']}) | {pred.border_delay_days:.1f} |
                | Customs clearance | {pred.customs_days_min}–{pred.customs_days_max} |
                | **Total window** | **{(pred.arrival_optimistic-pred.effective_departure).days}–{(pred.arrival_conservative-pred.effective_departure).days}** |
                """)
            with bc2:
                st.markdown(f"""
                | Key date | Value |
                |---|---|
                | Cargo ready | {pred.effective_departure.strftime('%d %b %Y')} |
                | Cut-off | {pred.cutoff_deadline.strftime('%d %b, %H:%M')} |
                | Best ETA | {pred.arrival_optimistic.strftime('%d %b %Y')} |
                | Realistic ETA | {pred.arrival_realistic.strftime('%d %b %Y')} |
                | Worst ETA | {pred.arrival_conservative.strftime('%d %b %Y')} |
                """)

        # ════════════════════════════════════════════════════════════════════
        # TAB 3 — MAP
        # ════════════════════════════════════════════════════════════════════
        with tab_map:
            with st.spinner("Building route map…"):
                map_html = build_map(payload, results)
            if map_html:
                st.caption("Solid arc = recommended · Faded = alternatives · "
                           "Hover for details · ⚠ = chokepoints")
                components.html(map_html, height=480, scrolling=False)
            else:
                st.info("Map unavailable — try a major city name.")

        # ════════════════════════════════════════════════════════════════════
        # TAB 4 — CO₂
        # ════════════════════════════════════════════════════════════════════
        with tab_co2:
            ctx = co2_context(payload, results)
            fig = build_co2_chart(payload, results)
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.metric("CO₂ — recommended", f"{ctx.get('best_co2',0):,.1f} kg")
            with mc2:
                st.metric("Equivalent car distance", f"{ctx.get('car_distance',0):,} km")
            with mc3:
                st.metric("Trees needed (1 yr)", f"{ctx.get('trees_year',0):,.1f}")
            if ctx.get("saving_vs_worst", 0) > 0:
                st.success(
                    f"🌿 **{ctx['best_mode']}** saves "
                    f"**{ctx['saving_vs_worst']:,.0f} kg CO₂** vs **{ctx['worst_mode']}**."
                )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Greyed bars = ineligible modes. "
                       "Intensity: air 0.602 · road 0.096 · rail 0.028 · sea FCL 0.010 kg CO₂/tonne-km.")

        # ════════════════════════════════════════════════════════════════════
        # TAB 5 — HANDLING INSTRUCTIONS
        # ════════════════════════════════════════════════════════════════════
        with tab_handling:
            instructions = get_instructions(payload, best.mode)
            category = payload["product"]["category"]
            flags    = payload["product"]["flags"]
            st.markdown(f"""
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                        padding:12px 16px;margin-bottom:16px;">
                <span style="font-size:13px;font-weight:600;color:#166534;">
                    📦 {category} &nbsp;·&nbsp; 🚀 {best.mode}
                </span>
            </div>""", unsafe_allow_html=True)

            SECTION_ORDER = ["packaging","labelling","temperature","stacking",
                             "storage","monitoring","mode_specific",
                             "documentation","regulatory"]
            for section in SECTION_ORDER:
                items = instructions.get(section, [])
                if not items:
                    continue
                with st.expander(f"{get_section_title(section)}  ({len(items)} points)",
                                 expanded=(section == "packaging")):
                    for item in items:
                        st.markdown(f"- {item}")

            lines = ["TRANSPORT & STORAGE INSTRUCTIONS", "="*50,
                     f"Product: {category}", f"Mode: {best.mode}", ""]
            for section in SECTION_ORDER:
                items = instructions.get(section, [])
                if not items:
                    continue
                lines += [get_section_title(section).upper(), "-"*40]
                lines += [f"• {i}" for i in items]
                lines.append("")
            st.download_button("⬇️ Download instructions (.txt)", "\n".join(lines),
                               file_name=f"handling_{category[:20].replace(' ','_')}.txt",
                               mime="text/plain")

        # ════════════════════════════════════════════════════════════════════
        # TAB 6 — WHY THIS MODE
        # ════════════════════════════════════════════════════════════════════
        with tab_why:
            if best.reasons:
                st.markdown("**Why this mode scored highest:**")
                for reason in best.reasons:
                    st.markdown(f"- {reason}")
            if best.flags:
                st.markdown("**Flags & notes:**")
                for f in best.flags:
                    icon = "⚠️" if f.level == "warn" else "ℹ️"
                    st.markdown(f"{icon} {f.message}")
            if len(eligible) > 1:
                st.markdown("---")
                st.markdown("**Alternative modes:**")
                for alt in eligible[1:]:
                    with st.expander(f"{alt.mode}  —  score {alt.score:.0f}/100"):
                        a1, a2, a3 = st.columns(3)
                        with a1:
                            d = alt.estimated_days
                            st.metric("Transit", f"{d[0]}–{d[1]} days")
                        with a2:
                            c2 = alt.estimated_cost_usd
                            st.metric("Est. cost", f"${c2[0]:,}–${c2[1]:,}")
                        with a3:
                            st.metric("CO₂", f"{alt.co2_kg:,.1f} kg")
                        for reason in alt.reasons[:4]:
                            st.markdown(f"- {reason}")
                        for flag in alt.flags:
                            st.markdown(f"⚠️ {flag.message}")
            if blocked:
                st.markdown("---")
                st.markdown("**Ineligible modes:**")
                for b in blocked:
                    with st.expander(f"~~{b.mode}~~  —  blocked"):
                        for f in b.flags:
                            st.markdown(f"🚫 {f.message}")
