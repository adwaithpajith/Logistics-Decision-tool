"""
arrival_predictor.py
────────────────────
Predicts estimated arrival date/time window given:
  - Departure datetime (user input)
  - Transport mode (from engine recommendation)
  - Route (origin/destination countries)
  - Number of border crossings
  - Payload constraints (urgency, etc.)

Accounts for:
  - Mode transit time range (from engine.py)
  - Public holidays at origin and destination
  - Weekend cutoffs per mode
  - Port/airport cargo cut-off times
  - Customs clearance working days at destination
  - Border crossing delay buffers
  - Confidence band (optimistic / realistic / conservative)
"""

from datetime import datetime, date, timedelta
from dataclasses import dataclass
import holidays as hol


# ── Country code mapping (country name → ISO-2) ──────────────────────────────

COUNTRY_ISO2: dict[str, str] = {
    "Afghanistan": "AF", "Algeria": "DZ", "Argentina": "AR",
    "Australia": "AU", "Austria": "AT", "Bangladesh": "BD",
    "Belgium": "BE", "Brazil": "BR", "Cambodia": "KH",
    "Canada": "CA", "Chile": "CL", "China": "CN",
    "Colombia": "CO", "Croatia": "HR", "Czech Republic": "CZ",
    "Denmark": "DK", "Egypt": "EG", "Ethiopia": "ET",
    "Finland": "FI", "France": "FR", "Germany": "DE",
    "Ghana": "GH", "Greece": "GR", "Hong Kong": "HK",
    "Hungary": "HU", "India": "IN", "Indonesia": "ID",
    "Iran": "IR", "Iraq": "IQ", "Ireland": "IE",
    "Israel": "IL", "Italy": "IT", "Japan": "JP",
    "Jordan": "JO", "Kenya": "KE", "Malaysia": "MY",
    "Mexico": "MX", "Morocco": "MA", "Myanmar": "MM",
    "Netherlands": "NL", "New Zealand": "NZ", "Nigeria": "NG",
    "Norway": "NO", "Pakistan": "PK", "Peru": "PE",
    "Philippines": "PH", "Poland": "PL", "Portugal": "PT",
    "Qatar": "QA", "Romania": "RO", "Russia": "RU",
    "Saudi Arabia": "SA", "Singapore": "SG", "South Africa": "ZA",
    "South Korea": "KR", "Spain": "ES", "Sri Lanka": "LK",
    "Sweden": "SE", "Switzerland": "CH", "Taiwan": "TW",
    "Thailand": "TH", "Turkey": "TR", "UAE": "AE",
    "Uganda": "UG", "Ukraine": "UA", "United Kingdom": "GB",
    "United States": "US", "Vietnam": "VN", "Yemen": "YE",
    "Zimbabwe": "ZW",
}


def _get_holiday_set(country_name: str, year: int) -> set[date]:
    """Returns a set of public holiday dates for a country+year."""
    iso = COUNTRY_ISO2.get(country_name)
    if not iso:
        return set()
    try:
        h = hol.country_holidays(iso, years=year)
        return set(h.keys())
    except Exception:
        return set()


def _is_working_day(d: date, holiday_set: set[date]) -> bool:
    """True if the date is Mon–Fri and not a public holiday."""
    return d.weekday() < 5 and d not in holiday_set


def _next_working_day(d: date, holiday_set: set[date]) -> date:
    """Returns d itself if it's a working day, otherwise the next one."""
    while not _is_working_day(d, holiday_set):
        d += timedelta(days=1)
    return d


def _add_working_days(start: date, n: int, holiday_set: set[date]) -> date:
    """Adds n working days to start, skipping weekends and holidays."""
    current = start
    added = 0
    while added < n:
        current += timedelta(days=1)
        if _is_working_day(current, holiday_set):
            added += 1
    return current


# ── Mode-specific rules ───────────────────────────────────────────────────────

@dataclass
class ModeRules:
    # Hours before departure that cargo must be at terminal
    cutoff_hours: int
    # Modes that operate on weekends (sea vessels sail daily; road/air mostly do)
    operates_weekends: bool
    # Typical customs clearance days at destination (working days)
    customs_days_min: int
    customs_days_max: int
    # Extra buffer days per border crossing
    border_delay_days: float
    # Label for cut-off description
    cutoff_label: str


MODE_RULES: dict[str, ModeRules] = {
    "Air freight": ModeRules(
        cutoff_hours=4,
        operates_weekends=True,
        customs_days_min=1,
        customs_days_max=2,
        border_delay_days=0.25,   # air customs usually fast
        cutoff_label="4 hrs before departure",
    ),
    "Sea freight (FCL)": ModeRules(
        cutoff_hours=48,
        operates_weekends=False,  # CY cut-off typically Mon–Fri
        customs_days_min=2,
        customs_days_max=5,
        border_delay_days=0.0,    # sea has no intermediate borders
        cutoff_label="48 hrs before vessel departure (CY cut-off)",
    ),
    "Sea freight (LCL)": ModeRules(
        cutoff_hours=72,
        operates_weekends=False,
        customs_days_min=2,
        customs_days_max=5,
        border_delay_days=0.0,
        cutoff_label="72 hrs before vessel departure (CFS cut-off)",
    ),
    "Road freight": ModeRules(
        cutoff_hours=2,
        operates_weekends=False,  # most road freight avoids Sunday driving (EU hours regs)
        customs_days_min=1,
        customs_days_max=3,
        border_delay_days=0.5,    # each border = ~half a day delay on average
        cutoff_label="2 hrs before truck departure",
    ),
    "Rail freight": ModeRules(
        cutoff_hours=24,
        operates_weekends=False,
        customs_days_min=1,
        customs_days_max=3,
        border_delay_days=1.0,    # gauge changes, inspections
        cutoff_label="24 hrs before train departure",
    ),
    "Multimodal": ModeRules(
        cutoff_hours=48,
        operates_weekends=False,
        customs_days_min=2,
        customs_days_max=4,
        border_delay_days=0.5,
        cutoff_label="48 hrs before first-leg departure",
    ),
}


# ── Main predictor ────────────────────────────────────────────────────────────

@dataclass
class ArrivalPrediction:
    # Effective departure (after cut-off check)
    effective_departure: date
    cutoff_deadline: datetime
    missed_cutoff: bool

    # Transit components
    transit_days_min: int
    transit_days_max: int
    border_delay_days: float
    customs_days_min: int
    customs_days_max: int

    # Weather delay
    weather_delay_days: int           # extra days added due to live weather risk
    weather_delay_label: str          # human-readable reason, empty if no delay

    # Holiday hits
    origin_holidays_hit: list[tuple[date, str]]
    dest_holidays_hit: list[tuple[date, str]]

    # Final arrival window
    arrival_optimistic: date
    arrival_realistic: date
    arrival_conservative: date

    # Confidence
    confidence: str
    confidence_reason: str

    # Timeline
    timeline: list[dict]


def predict_arrival(
    departure_dt: datetime,
    mode: str,
    origin_country: str,
    dest_country: str,
    border_crossings: int,
    transit_days_min: int,
    transit_days_max: int,
    weather_risk_points: list[dict] | None = None,  # from risk_feed.fetch_route_risk
) -> ArrivalPrediction:

    rules     = MODE_RULES.get(mode, MODE_RULES["Road freight"])
    dep_date  = departure_dt.date()
    dep_year  = dep_date.year
    arr_year  = dep_year + 1   # cover year boundaries

    # ── Holiday sets ──────────────────────────────────────────────────────────
    origin_hols_dict: dict[date, str] = {}
    dest_hols_dict:   dict[date, str] = {}
    try:
        o_iso = COUNTRY_ISO2.get(origin_country)
        d_iso = COUNTRY_ISO2.get(dest_country)
        if o_iso:
            for yr in [dep_year, arr_year]:
                origin_hols_dict.update(hol.country_holidays(o_iso, years=yr))
        if d_iso:
            for yr in [dep_year, arr_year]:
                dest_hols_dict.update(hol.country_holidays(d_iso, years=yr))
    except Exception:
        pass

    origin_hols = set(origin_hols_dict.keys())
    dest_hols   = set(dest_hols_dict.keys())

    # ── Cut-off deadline ──────────────────────────────────────────────────────
    cutoff_deadline = departure_dt - timedelta(hours=rules.cutoff_hours)
    missed_cutoff   = False

    # Effective departure: if cargo cut-off is missed, push to next valid slot
    effective_dep = dep_date
    if departure_dt <= cutoff_deadline + timedelta(hours=rules.cutoff_hours):
        # User's departure time IS the stated departure — check if we're past cut-off
        # (here departure_dt means "I want to send it on this date")
        pass

    # If the departure day is a weekend/holiday and mode doesn't run, find next slot
    if not rules.operates_weekends:
        effective_dep = _next_working_day(dep_date, origin_hols)
        if effective_dep != dep_date:
            missed_cutoff = True   # had to push forward

    # ── Border delay (in calendar days) ──────────────────────────────────────
    total_border_delay = rules.border_delay_days * border_crossings

    # ── Weather delay buffer (from live risk feed) ────────────────────────────
    # Scans all chokepoints on the route and applies a buffer to the
    # conservative estimate based on the worst weather risk found.
    weather_delay_days  = 0
    weather_delay_label = ""
    worst_weather_rp    = None   # the chokepoint driving the worst risk

    RISK_RANK = {"high": 2, "medium": 1, "low": 0, "unknown": -1}

    if weather_risk_points:
        # Find the chokepoint with the worst weather risk
        worst_rank = -1
        for rp in weather_risk_points:
            if rp.get("_port_only"):
                continue
            w_risk = rp.get("weather_risk", "unknown")
            rank   = RISK_RANK.get(w_risk, -1)
            if rank > worst_rank:
                worst_rank      = rank
                worst_weather_rp = rp

        if worst_rank == 2:    # high
            weather_delay_days  = 3
            weather_delay_label = (
                f"🔴 High weather risk at {worst_weather_rp['name']} "
                f"({worst_weather_rp.get('weather_reason','adverse conditions')}) "
                f"— +{weather_delay_days} days added to worst-case estimate."
            )
        elif worst_rank == 1:  # medium
            weather_delay_days  = 1
            weather_delay_label = (
                f"🟡 Elevated weather at {worst_weather_rp['name']} "
                f"({worst_weather_rp.get('weather_reason','conditions to monitor')}) "
                f"— +{weather_delay_days} day added to worst-case estimate."
            )

    # ── Build arrival dates ───────────────────────────────────────────────────

    def _compute_arrival(transit: int, customs: int,
                         extra_days: int = 0) -> date:
        # 1. Add transit days
        if mode in ("Air freight", "Sea freight (FCL)", "Sea freight (LCL)"):
            arr = effective_dep + timedelta(days=transit)
        else:
            arr = _add_working_days(effective_dep, transit, origin_hols)

        # 2. Add border delays
        arr += timedelta(days=int(total_border_delay))
        if total_border_delay % 1 >= 0.5:
            arr += timedelta(days=1)

        # 3. Add weather buffer (only on conservative — extra_days > 0)
        arr += timedelta(days=extra_days)

        # 4. Next working day at destination
        arr = _next_working_day(arr, dest_hols)

        # 5. Customs clearance
        arr = _add_working_days(arr, customs, dest_hols)

        return arr

    arrival_optimistic   = _compute_arrival(transit_days_min, rules.customs_days_min)
    arrival_conservative = _compute_arrival(transit_days_max, rules.customs_days_max,
                                            extra_days=weather_delay_days)

    # Realistic: weighted midpoint — add half the weather buffer
    mid_transit  = (transit_days_min + transit_days_max * 2) // 3
    mid_customs  = (rules.customs_days_min + rules.customs_days_max + 1) // 2
    mid_weather  = weather_delay_days // 2
    arrival_realistic = _compute_arrival(mid_transit, mid_customs,
                                         extra_days=mid_weather)

    # ── Detect holiday hits in transit window ─────────────────────────────────
    origin_holidays_hit = []
    dest_holidays_hit   = []

    # Check origin holidays in first few days (export processing)
    for i in range(5):
        d = effective_dep + timedelta(days=i)
        if d in origin_hols_dict:
            origin_holidays_hit.append((d, origin_hols_dict[d]))

    # Check destination holidays near arrival window
    for i in range(int((arrival_conservative - arrival_optimistic).days) + 10):
        d = arrival_optimistic + timedelta(days=i)
        if d in dest_hols_dict:
            dest_holidays_hit.append((d, dest_hols_dict[d]))

    # ── Confidence assessment ─────────────────────────────────────────────────
    spread_days = (arrival_conservative - arrival_optimistic).days
    issues = []
    if missed_cutoff:           issues.append("departure pushed due to weekend/holiday")
    if origin_holidays_hit:     issues.append(f"{len(origin_holidays_hit)} holiday(s) at origin")
    if dest_holidays_hit:       issues.append(f"{len(dest_holidays_hit)} holiday(s) at destination")
    if border_crossings > 2:    issues.append(f"{border_crossings} border crossings")
    if spread_days > 14:        issues.append("wide transit range")
    if weather_delay_days >= 3: issues.append("high weather risk on route")
    elif weather_delay_days >= 1: issues.append("elevated weather risk on route")

    if len(issues) == 0:
        confidence = "High"
        confidence_reason = "No holidays, no border delays, and a tight transit range."
    elif len(issues) <= 2:
        confidence = "Medium"
        confidence_reason = "Some variables: " + "; ".join(issues) + "."
    else:
        confidence = "Low"
        confidence_reason = "Multiple uncertainty factors: " + "; ".join(issues) + "."

    # ── Timeline ──────────────────────────────────────────────────────────────
    timeline = [
        {
            "label": "📅 Cargo ready / departure",
            "date":  effective_dep,
            "note":  f"Cut-off: cargo must be at terminal by {cutoff_deadline.strftime('%d %b %Y, %H:%M')}",
        },
        {
            "label": "🚀 In transit",
            "date":  effective_dep + timedelta(days=1),
            "note":  f"{transit_days_min}–{transit_days_max} days transit via {mode}",
        },
    ]

    if border_crossings > 0:
        border_date = effective_dep + timedelta(days=max(1, transit_days_min // 2))
        timeline.append({
            "label": f"🛃 Border crossing(s) ×{border_crossings}",
            "date":  border_date,
            "note":  f"~{total_border_delay:.1f} days added for customs inspection",
        })

    if weather_delay_days > 0:
        weather_date = effective_dep + timedelta(days=max(2, transit_days_min // 2 + 1))
        timeline.append({
            "label": "🌩 Weather delay buffer",
            "date":  weather_date,
            "note":  weather_delay_label,
        })

    timeline.append({
        "label": "🏁 Arrives at destination port/airport",
        "date":  arrival_optimistic,
        "note":  "Earliest possible — pending customs clearance",
    })

    if rules.customs_days_min > 0:
        timeline.append({
            "label": "📋 Customs clearance",
            "date":  arrival_optimistic,
            "note":  f"{rules.customs_days_min}–{rules.customs_days_max} working days",
        })

    timeline.append({
        "label": "✅ Estimated delivery",
        "date":  arrival_realistic,
        "note":  f"Realistic estimate · Window: {arrival_optimistic.strftime('%d %b')} – {arrival_conservative.strftime('%d %b %Y')}",
    })

    return ArrivalPrediction(
        effective_departure    = effective_dep,
        cutoff_deadline        = cutoff_deadline,
        missed_cutoff          = missed_cutoff,
        transit_days_min       = transit_days_min,
        transit_days_max       = transit_days_max,
        border_delay_days      = total_border_delay,
        customs_days_min       = rules.customs_days_min,
        customs_days_max       = rules.customs_days_max,
        weather_delay_days     = weather_delay_days,
        weather_delay_label    = weather_delay_label,
        origin_holidays_hit    = origin_holidays_hit,
        dest_holidays_hit      = dest_holidays_hit,
        arrival_optimistic     = arrival_optimistic,
        arrival_realistic      = arrival_realistic,
        arrival_conservative   = arrival_conservative,
        confidence             = confidence,
        confidence_reason      = confidence_reason,
        timeline               = timeline,
    )
