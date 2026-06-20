"""
Transport Decision Engine
─────────────────────────
Takes the structured payload from app.py and scores each transport mode.
Returns a ranked list of recommendations with explanations.
"""

from dataclasses import dataclass, field
from typing import Optional

# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class Flag:
    """A rule that fired during evaluation — shown in the explanation panel."""
    level: str          # "block" | "warn" | "info"
    mode: str           # which mode this applies to, or "all"
    message: str


@dataclass
class ModeResult:
    mode: str
    eligible: bool
    score: float                    # 0–100, higher = better fit
    estimated_days: Optional[tuple] # (min, max) transit days
    estimated_cost_usd: Optional[tuple]  # (min, max)
    co2_kg: Optional[float]         # kg CO₂ per tonne of cargo
    flags: list[Flag] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


# ── Cost & transit reference tables ─────────────────────────────────────────
# Rough industry averages — good enough for a portfolio tool.
# Format: (usd_per_kg, transit_days_min, transit_days_max, co2_per_tonne_km)

MODE_REFERENCE = {
    "Air freight": {
        "cost_per_kg": 4.5,
        "days": (1, 5),
        "co2_per_tonne_km": 0.602,   # kg CO₂
    },
    "Sea freight (FCL)": {
        "cost_per_kg": 0.04,
        "days": (14, 35),
        "co2_per_tonne_km": 0.010,
    },
    "Sea freight (LCL)": {
        "cost_per_kg": 0.12,
        "days": (18, 40),
        "co2_per_tonne_km": 0.012,
    },
    "Road freight": {
        "cost_per_kg": 0.25,
        "days": (1, 10),
        "co2_per_tonne_km": 0.096,
    },
    "Rail freight": {
        "cost_per_kg": 0.08,
        "days": (5, 20),
        "co2_per_tonne_km": 0.028,
    },
    "Multimodal": {
        "cost_per_kg": 0.18,
        "days": (10, 25),
        "co2_per_tonne_km": 0.045,
    },
}

# Urgency → max acceptable transit days
URGENCY_DAYS = {
    "Not urgent (30+ days fine)":       35,
    "Standard (10–20 days)":            20,
    "Urgent (3–7 days)":                 7,
    "Critical (next day / same day)":    1,
}

# Carbon priority → max acceptable CO₂/tonne-km
CARBON_CEILING = {
    "Not a concern":                     999,
    "Nice to minimise":                  0.5,
    "Important":                         0.1,
    "Critical — lowest emissions only":  0.03,
}


# ── Distance-scaled transit time ─────────────────────────────────────────────
# MODE_REFERENCE["days"] holds a baseline range, but actual transit time
# depends heavily on distance. A flat (14, 35) day range for ALL sea routes
# regardless of distance unfairly penalises mid-range intercontinental routes
# (e.g. India→Europe at ~7,500km) against the urgency window, when in reality
# that route takes closer to 18-24 days, not 35.
#
# Reference speeds (km/day) approximate real-world average transit speed
# including port dwell time, not just sailing/flying speed.
MODE_AVG_SPEED_KM_DAY = {
    "Air freight":        2200,   # includes customs/handling, not pure flight speed
    "Sea freight (FCL)":   450,
    "Sea freight (LCL)":   420,   # slightly slower due to consolidation
    "Road freight":         550,
    "Rail freight":         600,
    "Multimodal":           500,
}

# Minimum transit floor (handling/customs at origin+destination even for short hops)
MODE_MIN_DAYS_FLOOR = {
    "Air freight":        1,
    "Sea freight (FCL)":  7,
    "Sea freight (LCL)":  9,
    "Road freight":       1,
    "Rail freight":       3,
    "Multimodal":         5,
}


def get_transit_days(mode: str, distance_km: float) -> tuple[int, int]:
    """
    Returns (min_days, max_days) scaled to actual distance, instead of using
    a flat reference range. Falls back to MODE_REFERENCE baseline if mode
    unknown.
    """
    speed = MODE_AVG_SPEED_KM_DAY.get(mode)
    floor = MODE_MIN_DAYS_FLOOR.get(mode, 1)
    if not speed:
        return MODE_REFERENCE.get(mode, {}).get("days", (1, 10))

    base_days = distance_km / speed
    d_min = max(floor, round(base_days * 0.85))
    d_max = max(d_min + 1, round(base_days * 1.35))

    return (int(d_min), int(d_max))


# ── Hard eligibility rules ───────────────────────────────────────────────────

def check_eligibility(mode: str, p: dict, r: dict, c: dict) -> list[Flag]:
    """
    Returns a list of Flag(level='block', ...) if the mode is ineligible.
    Also returns warnings (level='warn') for soft issues.
    """
    flags = []
    product_flags = p.get("flags", [])
    infra          = r.get("infra_available", [])
    dist           = r.get("distance_km", 0)
    excluded       = c.get("excluded_modes", [])
    urgency_days   = URGENCY_DAYS.get(c.get("urgency", "Standard (10–20 days)"), 20)
    weight         = p.get("weight_kg", 0)
    budget         = c.get("budget_usd", 0)

    ref = MODE_REFERENCE.get(mode, {})
    transit_min, transit_max = get_transit_days(mode, dist)
    est_cost    = ref.get("cost_per_kg", 0) * weight

    # ── User exclusions ──────────────────────────────────────────────────────
    if mode in excluded:
        flags.append(Flag("block", mode, "Excluded by user preference."))
        return flags   # no point checking further

    # ── Infrastructure ───────────────────────────────────────────────────────
    if mode in ("Sea freight (FCL)", "Sea freight (LCL)"):
        if "sea" not in infra:
            flags.append(Flag("block", mode, "No seaport available at destination."))
    if mode == "Air freight":
        if "air" not in infra:
            flags.append(Flag("block", mode, "No airport available at destination."))
    if mode == "Rail freight":
        if "rail" not in infra:
            flags.append(Flag("block", mode, "No rail terminal at destination."))
    if mode == "Road freight":
        if "road" not in infra:
            flags.append(Flag("block", mode, "No road access at destination."))

    # ── Distance constraints ─────────────────────────────────────────────────
    if mode in ("Sea freight (FCL)", "Sea freight (LCL)") and dist < 500:
        flags.append(Flag("block", mode, f"Sea freight not viable under 500 km (distance: {dist} km)."))
    if mode == "Road freight" and dist > 5000:
        flags.append(Flag("block", mode, f"Road freight not feasible beyond 5,000 km (distance: {dist} km)."))
    if mode == "Rail freight" and dist < 300:
        flags.append(Flag("block", mode, f"Rail not economical under 300 km (distance: {dist} km)."))

    # ── Hazmat rules ─────────────────────────────────────────────────────────
    if "hazmat" in product_flags:
        if mode == "Air freight":
            flags.append(Flag("block", mode,
                "Hazardous materials are restricted on air freight (IATA DG regulations). "
                "Special IATA DG approval required — assumed unavailable."))
        else:
            flags.append(Flag("warn", mode,
                "Hazmat: ensure ADR/IMDG compliance and correct documentation."))

    # ── Live animals ─────────────────────────────────────────────────────────
    if p.get("category") == "Live animals":
        if mode in ("Sea freight (FCL)", "Sea freight (LCL)", "Rail freight"):
            flags.append(Flag("warn", mode,
                "Live animals via this mode require CITES permits and welfare compliance checks."))

    # ── Oversized cargo ──────────────────────────────────────────────────────
    if p.get("category") == "Oversized / heavy machinery":
        if mode == "Air freight":
            flags.append(Flag("block", mode,
                "Air freight cannot accommodate oversized / heavy machinery in standard configurations."))
        else:
            flags.append(Flag("warn", mode,
                "Oversized cargo: confirm dimensional and weight limits with carrier."))

    # ── Bulk liquids ─────────────────────────────────────────────────────────
    if "bulk" in product_flags or p.get("category") == "Liquid bulk (chemicals/fuel)":
        if mode == "Air freight":
            flags.append(Flag("block", mode, "Bulk liquid cargo is not compatible with air freight."))
        if mode in ("Road freight", "Rail freight"):
            flags.append(Flag("warn", mode, "Bulk liquid requires tanker trucks or tank wagons — confirm availability."))

    # ── Urgency vs transit ───────────────────────────────────────────────────
    if transit_max > urgency_days:
        flags.append(Flag("block", mode,
            f"Transit time ({transit_max} days max) exceeds urgency window ({urgency_days} days)."))

    # ── Budget ───────────────────────────────────────────────────────────────
    if budget > 0 and est_cost > budget * 1.2:   # 20% tolerance
        flags.append(Flag("warn", mode,
            f"Estimated cost (${est_cost:,.0f}) likely exceeds your budget (${budget:,.0f})."))

    # ── High-value goods ─────────────────────────────────────────────────────
    if "high_value" in product_flags:
        if mode == "Sea freight (LCL)":
            flags.append(Flag("warn", mode,
                "LCL consolidation increases handling risk for high-value goods. FCL preferred."))

    return flags


# ── Scoring function ─────────────────────────────────────────────────────────

def score_mode(mode: str, p: dict, r: dict, c: dict, elig_flags: list[Flag]) -> tuple[float, list[str]]:
    """
    Returns (score 0–100, list of positive reasons).
    Only called if mode is eligible.
    """
    score   = 50.0   # baseline
    reasons = []

    dist           = r.get("distance_km", 0)
    weight         = p.get("weight_kg", 0)
    volume         = p.get("volume_m3", 0)
    product_flags  = p.get("flags", [])
    urgency        = c.get("urgency", "Standard (10–20 days)")
    urgency_days   = URGENCY_DAYS.get(urgency, 20)
    carbon_p       = c.get("carbon_priority", "Nice to minimise")
    carbon_ceil    = CARBON_CEILING.get(carbon_p, 999)
    reliability    = c.get("reliability", "Moderate")
    preferred      = c.get("preferred_modes", [])
    budget         = c.get("budget_usd", 0)
    category       = p.get("category", "")

    ref     = MODE_REFERENCE[mode]
    co2     = ref["co2_per_tonne_km"]
    cost_kg = ref["cost_per_kg"]
    d_min, d_max = get_transit_days(mode, dist)

    # ── Speed bonus/penalty ──────────────────────────────────────────────────
    if urgency_days <= 1:
        speed_map = {"Air freight": +30, "Road freight": +10, "Multimodal": -10,
                     "Sea freight (FCL)": -20, "Sea freight (LCL)": -25, "Rail freight": -10}
    elif urgency_days <= 7:
        speed_map = {"Air freight": +20, "Road freight": +15, "Multimodal": +5,
                     "Rail freight": 0, "Sea freight (FCL)": -15, "Sea freight (LCL)": -20}
    elif urgency_days <= 20:
        speed_map = {"Air freight": 0, "Road freight": +5, "Multimodal": +10,
                     "Rail freight": +10, "Sea freight (FCL)": +10, "Sea freight (LCL)": +5}
    else:
        speed_map = {"Air freight": -10, "Road freight": 0, "Multimodal": +5,
                     "Rail freight": +10, "Sea freight (FCL)": +20, "Sea freight (LCL)": +15}

    s_bonus = speed_map.get(mode, 0)
    score += s_bonus
    if s_bonus >= 10:
        reasons.append(f"Transit time ({d_min}–{d_max} days) fits urgency window well.")
    elif s_bonus <= -10:
        reasons.append(f"Transit time ({d_min}–{d_max} days) is slower than ideal for this urgency.")

    # ── Carbon bonus ─────────────────────────────────────────────────────────
    if co2 < carbon_ceil:
        c_bonus = min(20, int((carbon_ceil - co2) / carbon_ceil * 20))
        score += c_bonus
        if c_bonus >= 10:
            reasons.append(f"Low emissions ({co2} kg CO₂/tonne-km) aligns with your carbon priority.")
    else:
        score -= 15
        reasons.append(f"Emissions ({co2} kg CO₂/tonne-km) exceed your carbon ceiling ({carbon_ceil}).")

    # ── Distance fit ─────────────────────────────────────────────────────────
    if mode == "Air freight" and dist > 8000:
        score += 10
        reasons.append("Long intercontinental distance — air is often the only practical option.")
    if mode in ("Sea freight (FCL)", "Sea freight (LCL)") and dist > 3000:
        score += 15
        reasons.append("Long distance makes sea freight the most cost-effective option.")
    if mode == "Road freight" and dist < 1500:
        score += 15
        reasons.append("Short distance makes road freight fast and cost-efficient.")
    if mode == "Rail freight" and 800 < dist < 8000:
        score += 10
        reasons.append("Rail freight is efficient over medium-to-long continental distances.")
    if mode == "Multimodal" and dist > 2000:
        score += 8
        reasons.append("Long route benefits from combining sea/rail with road for last-mile.")

    # ── Weight/volume optimisation ───────────────────────────────────────────
    if mode == "Sea freight (FCL)" and (weight > 5000 or volume > 20):
        score += 12
        reasons.append("Heavy/large shipment — FCL gives best rate per kg at this scale.")
    if mode == "Sea freight (LCL)" and weight < 2000 and volume < 15:
        score += 10
        reasons.append("Smaller shipment — LCL avoids paying for unused container space.")
    if mode == "Air freight" and weight < 500:
        score += 8
        reasons.append("Light shipment — air freight cost is manageable at this weight.")

    # ── Special product fit ───────────────────────────────────────────────────
    if "temperature_controlled" in product_flags:
        if mode == "Air freight":
            score += 12
            reasons.append("Air freight offers the shortest exposure time for cold-chain goods.")
        if mode in ("Sea freight (FCL)",) and dist > 3000:
            score += 5
            reasons.append("Reefer containers maintain cold chain over long sea routes.")

    if "fragile" in product_flags:
        if mode == "Air freight":
            score += 8
            reasons.append("Air freight involves less handling and vibration — better for fragile goods.")
        if mode == "Sea freight (LCL)":
            score -= 8
            reasons.append("LCL consolidation involves extra handling — higher risk for fragile goods.")

    if "high_value" in product_flags:
        if mode == "Air freight":
            score += 10
            reasons.append("Air freight provides faster clearance and more secure handling for high-value goods.")

    if category == "Bulk commodities (grain/coal/ore)":
        if mode in ("Sea freight (FCL)", "Rail freight"):
            score += 15
            reasons.append("Bulk commodities are best suited to sea or rail — designed for large volumes at low cost.")
        if mode == "Air freight":
            score -= 20
            reasons.append("Air freight is cost-prohibitive for bulk commodities.")

    if category in ("E-commerce parcels", "Garments & textiles") and weight < 200:
        if mode == "Air freight":
            score += 10
            reasons.append("E-commerce / apparel parcels are typically air-freighted for speed.")

    # ── Reliability ───────────────────────────────────────────────────────────
    if reliability in ("High", "Mission-critical"):
        if mode == "Air freight":
            score += 8
            reasons.append("Air freight offers most predictable schedules.")
        if mode == "Sea freight (LCL)":
            score -= 5
            reasons.append("LCL schedules can be less reliable due to consolidation delays.")

    # ── Budget fit ───────────────────────────────────────────────────────────
    if budget > 0:
        est_cost = cost_kg * weight
        if est_cost <= budget * 0.6:
            score += 10
            reasons.append(f"Estimated cost (${est_cost:,.0f}) is comfortably within budget.")
        elif est_cost <= budget:
            score += 5
        else:
            score -= 5

    # ── User preference ───────────────────────────────────────────────────────
    if mode in preferred:
        score += 15
        reasons.append("Matches your stated mode preference.")

    # ── Warn flags reduce score slightly ─────────────────────────────────────
    warn_count = sum(1 for f in elig_flags if f.level == "warn")
    score -= warn_count * 5

    return max(0.0, min(100.0, score)), reasons


# ── Estimate cost and transit ────────────────────────────────────────────────

def estimate(mode: str, weight_kg: float, distance_km: float) -> tuple:
    ref = MODE_REFERENCE[mode]
    base_cost = ref["cost_per_kg"] * weight_kg
    # Add a rough distance surcharge for long routes
    dist_factor = 1 + (distance_km / 20_000)
    cost_lo = base_cost * dist_factor * 0.8
    cost_hi = base_cost * dist_factor * 1.3
    d_min, d_max = get_transit_days(mode, distance_km)
    co2 = ref["co2_per_tonne_km"] * (weight_kg / 1000) * distance_km
    return (cost_lo, cost_hi), (d_min, d_max), co2


# ── Main entry point ─────────────────────────────────────────────────────────

def evaluate(payload: dict) -> list[ModeResult]:
    """
    Takes the full payload dict from app.py.
    Returns a list of ModeResult, sorted best → worst.
    """
    p = payload.get("product", {})
    r = payload.get("route", {})
    c = payload.get("constraints", {})

    weight   = p.get("weight_kg", 1)
    distance = r.get("distance_km", 1000)

    results = []

    for mode in MODE_REFERENCE:
        flags = check_eligibility(mode, p, r, c)

        blocked = any(f.level == "block" for f in flags)

        if blocked:
            results.append(ModeResult(
                mode=mode,
                eligible=False,
                score=0,
                estimated_days=None,
                estimated_cost_usd=None,
                co2_kg=None,
                flags=flags,
                reasons=[],
            ))
        else:
            score, reasons = score_mode(mode, p, r, c, flags)
            cost_range, day_range, co2 = estimate(mode, weight, distance)
            results.append(ModeResult(
                mode=mode,
                eligible=True,
                score=round(score, 1),
                estimated_days=day_range,
                estimated_cost_usd=(round(cost_range[0]), round(cost_range[1])),
                co2_kg=round(co2, 1),
                flags=flags,
                reasons=reasons,
            ))

    # Sort: eligible first, then by score descending
    results.sort(key=lambda x: (not x.eligible, -x.score))
    return results
