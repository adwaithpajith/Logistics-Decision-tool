"""
co2_chart.py
────────────
Builds a Plotly chart comparing CO₂ emissions across all transport modes
for a given shipment. Shows:
  • Bar chart — total kg CO₂ per mode (eligible vs blocked)
  • Reference lines — car equivalent, transatlantic flight equivalent
  • Colour-coded by mode, greyed out for ineligible
  • Breakdown annotation: kg CO₂/tonne-km × tonnes × km
"""

import plotly.graph_objects as go


# ── Mode colours (match map_view.py) ─────────────────────────────────────────
MODE_COLOUR = {
    "Air freight":       "#6366f1",
    "Sea freight (FCL)": "#0ea5e9",
    "Sea freight (LCL)": "#38bdf8",
    "Road freight":      "#f97316",
    "Rail freight":      "#a855f7",
    "Multimodal":        "#10b981",
}

MODE_ICON = {
    "Air freight":       "✈",
    "Sea freight (FCL)": "🚢",
    "Sea freight (LCL)": "🚢",
    "Road freight":      "🚛",
    "Rail freight":      "🚂",
    "Multimodal":        "🔀",
}

# kg CO₂ per tonne-km (matches engine.py)
CO2_INTENSITY = {
    "Air freight":       0.602,
    "Sea freight (FCL)": 0.010,
    "Sea freight (LCL)": 0.012,
    "Road freight":      0.096,
    "Rail freight":      0.028,
    "Multimodal":        0.045,
}

# ── Reference equivalents ─────────────────────────────────────────────────────
# kg CO₂
REF_CAR_KM          = 0.21    # average car per km
REF_FLIGHT_PAX_KM   = 0.255   # economy flight per passenger-km
TRANSATLANTIC_KM    = 8_700   # ~London to New York


def build_co2_chart(payload: dict, results: list) -> go.Figure:
    """
    payload  — shipment payload dict
    results  — list of ModeResult from engine.evaluate()
    Returns a Plotly Figure.
    """
    weight_kg   = payload["product"]["weight_kg"]
    distance_km = payload["route"]["distance_km"]
    weight_t    = weight_kg / 1000

    best_mode = next((r.mode for r in results if r.eligible), None)

    # ── Build bar data ────────────────────────────────────────────────────────
    modes, co2_vals, colours, opacities, labels, hover = [], [], [], [], [], []

    for res in results:
        intensity = CO2_INTENSITY[res.mode]
        co2       = intensity * weight_t * distance_km

        modes.append(res.mode)
        co2_vals.append(round(co2, 1))
        colours.append(MODE_COLOUR.get(res.mode, "#94a3b8"))
        opacities.append(1.0 if res.eligible else 0.25)

        # Short label with icon
        labels.append(f"{MODE_ICON.get(res.mode,'')} {res.mode}")

        status = "✅ Eligible" if res.eligible else "❌ Ineligible"
        equiv_cars  = co2 / (REF_CAR_KM * distance_km)
        hover.append(
            f"<b>{res.mode}</b><br>"
            f"CO₂: <b>{co2:,.1f} kg</b><br>"
            f"Intensity: {intensity} kg/tonne-km<br>"
            f"= {equiv_cars:.1f}× a car over same distance<br>"
            f"{status}"
        )

    # Sort by CO₂ ascending
    sorted_data = sorted(zip(co2_vals, modes, colours, opacities, labels, hover))
    co2_vals, modes, colours, opacities, labels, hover = map(list, zip(*sorted_data))

    # ── Reference values ──────────────────────────────────────────────────────
    transatlantic_co2 = REF_FLIGHT_PAX_KM * TRANSATLANTIC_KM  # ~2,218 kg per pax
    car_equiv_co2     = REF_CAR_KM * distance_km               # car over same distance

    # ── Figure ────────────────────────────────────────────────────────────────
    fig = go.Figure()

    # Bars
    fig.add_trace(go.Bar(
        x=labels,
        y=co2_vals,
        marker=dict(
            color=colours,
            opacity=opacities,
            line=dict(width=0),
        ),
        customdata=list(zip(modes, co2_vals, opacities)),
        hovertemplate="%{text}<extra></extra>",
        text=hover,
        textposition="none",
        name="CO₂ (kg)",
    ))

    # Value labels on bars
    for i, (label, val, opa) in enumerate(zip(labels, co2_vals, opacities)):
        fig.add_annotation(
            x=label, y=val,
            text=f"<b>{val:,.0f}</b> kg",
            showarrow=False,
            yanchor="bottom",
            yshift=6,
            font=dict(size=12, color="#374151" if opa == 1.0 else "#9ca3af"),
        )

    # Best mode marker
    if best_mode:
        best_label = f"{MODE_ICON.get(best_mode,'')} {best_mode}"
        if best_label in labels:
            best_co2 = co2_vals[labels.index(best_label)]
            fig.add_annotation(
                x=best_label, y=best_co2,
                text="★ Recommended",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#1d4ed8",
                ax=0, ay=-40,
                font=dict(size=11, color="#1d4ed8"),
                bgcolor="rgba(239,246,255,0.9)",
                bordercolor="#93c5fd",
                borderwidth=1,
                borderpad=4,
            )

    # Reference line — car over same distance
    fig.add_hline(
        y=car_equiv_co2,
        line=dict(color="#f59e0b", width=1.5, dash="dot"),
        annotation_text=f"🚗 Car over {distance_km:,} km ({car_equiv_co2:,.0f} kg CO₂)",
        annotation_position="top right",
        annotation_font=dict(size=11, color="#92400e"),
    )

    # Reference line — transatlantic flight (only if in range)
    max_val = max(co2_vals) if co2_vals else 1
    if transatlantic_co2 < max_val * 2.5:
        fig.add_hline(
            y=transatlantic_co2,
            line=dict(color="#6b7280", width=1.2, dash="dash"),
            annotation_text=f"✈ Transatlantic flight/pax ({transatlantic_co2:,.0f} kg CO₂)",
            annotation_position="bottom right",
            annotation_font=dict(size=11, color="#4b5563"),
        )

    # ── Styling ───────────────────────────────────────────────────────────────
    saving_vs_air = None
    if best_mode and best_mode != "Air freight":
        air_co2  = CO2_INTENSITY["Air freight"] * weight_t * distance_km
        best_co2_val = CO2_INTENSITY[best_mode] * weight_t * distance_km
        saving_vs_air = air_co2 - best_co2_val

    subtitle = (
        f"{weight_kg:,.0f} kg cargo · {distance_km:,} km · "
        + (f"Recommended mode saves <b>{saving_vs_air:,.0f} kg CO₂</b> vs air freight"
           if saving_vs_air and saving_vs_air > 0 else "All eligible modes shown")
    )

    fig.update_layout(
        title=dict(
            text=f"CO₂ emissions by transport mode<br><sup>{subtitle}</sup>",
            x=0.0,
            xanchor="left",
            font=dict(size=16),
        ),
        xaxis=dict(
            title=None,
            tickfont=dict(size=12),
            showgrid=False,
        ),
        yaxis=dict(
            title="Total CO₂ (kg)",
            showgrid=True,
            gridcolor="#f1f5f9",
            gridwidth=1,
            zeroline=False,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=80, b=20, l=60, r=20),
        showlegend=False,
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e2e8f0",
            font_size=13,
        ),
        height=400,
    )

    return fig


def co2_context(payload: dict, results: list) -> dict:
    """
    Returns a dict of plain-English context figures for display
    alongside the chart.
    """
    weight_kg   = payload["product"]["weight_kg"]
    distance_km = payload["route"]["distance_km"]
    weight_t    = weight_kg / 1000

    best = next((r for r in results if r.eligible), None)
    worst_eligible = next((r for r in reversed(results) if r.eligible), None)

    ctx = {}

    if best:
        best_co2 = CO2_INTENSITY[best.mode] * weight_t * distance_km
        ctx["best_mode"]    = best.mode
        ctx["best_co2"]     = round(best_co2, 1)
        ctx["car_distance"] = round(best_co2 / REF_CAR_KM)   # km a car would travel

        # Tree absorption: avg tree absorbs ~22 kg CO₂/year
        ctx["trees_year"] = round(best_co2 / 22, 1)

    if best and worst_eligible and best.mode != worst_eligible.mode:
        worst_co2   = CO2_INTENSITY[worst_eligible.mode] * weight_t * distance_km
        best_co2    = CO2_INTENSITY[best.mode] * weight_t * distance_km
        ctx["saving_vs_worst"] = round(worst_co2 - best_co2, 1)
        ctx["worst_mode"]      = worst_eligible.mode

    return ctx
