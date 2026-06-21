# 🚚 Transport Advisor — Logistics Decision Tool

A Streamlit app that recommends the best freight transport mode for a shipment — weighing cost, transit time, CO₂ footprint, and route risk — and explains *why*.

**🔗 Live app:** [logibrain.streamlit.app](https://logibrain.streamlit.app/)

---

## What it does

You describe a shipment — product, weight/volume, special handling needs, origin/destination, urgency, and constraints — and the app:

1. **Scores every transport mode** (Air, Sea FCL, Sea LCL, Road, Rail, Multimodal) against your shipment, flagging which are eligible and which are blocked, with a ranked recommendation.
2. **Predicts an arrival window**, accounting for transit time ranges, public holidays at origin/destination, weekend cutoffs, port/airport cargo cut-off times, customs clearance days, and border crossing delays.
3. **Pulls live route risk** — weather at chokepoints, recent significant earthquakes, and (where available) port congestion / vessel arrival data.
4. **Plots the route** on an interactive map with great-circle arcs for the recommended and alternative modes, plus chokepoint markers.
5. **Compares CO₂ emissions** across all modes with reference equivalents (car trip, transatlantic flight).
6. **Generates handling instructions** — packaging, labelling, temperature, stacking, storage, documentation, and regulatory notes — tailored to the product category and chosen mode.
7. **Explains the recommendation** in plain language, so the "why" behind the ranking is never a black box.

## Features at a glance

| Tab | What it shows |
|---|---|
| 🛰️ Live risk | Weather and seismic risk near route chokepoints, port congestion signals |
| 🕐 Arrival prediction | Estimated arrival window with confidence bands (optimistic / realistic / conservative) |
| 🗺️ Route map | Origin/destination markers, route arcs, chokepoints |
| 🌿 CO₂ comparison | Per-mode emissions chart with real-world equivalents |
| 📦 Handling instructions | Packaging, labelling, storage, and compliance guidance |
| 💡 Why this mode? | Plain-English breakdown of the scoring and eligibility logic |

## Project structure

```
logistics_tool/
├── app.py                    # Streamlit UI — input form + results tabs
├── engine.py                 # Decision engine — eligibility checks & mode scoring
├── arrival_predictor.py      # Arrival date/time window prediction
├── map_view.py                # Folium route map (coords, arcs, chokepoints)
├── co2_chart.py               # Plotly CO₂ emissions comparison chart
├── risk_feed.py               # Live weather / seismic / port risk data
├── handling_instructions.py   # Packaging & compliance instruction library
├── requirements.txt
└── README.md
```

## Tech stack

- **[Streamlit](https://streamlit.io/)** — UI and app framework
- **[Plotly](https://plotly.com/python/)** — CO₂ comparison chart
- **[Folium](https://python-visualization.github.io/folium/)** — interactive route map
- **[holidays](https://pypi.org/project/holidays/)** — public holiday lookups for arrival prediction
- **OpenWeatherMap, USGS Earthquake Hazards, VesselFinder** — live risk data feeds

## Running locally

```bash
git clone <your-repo-url>
cd logistics_tool
pip install -r requirements.txt
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### API keys

The live risk feed (`risk_feed.py`) uses three data sources:

| Source | Key required | Get one at |
|---|---|---|
| OpenWeatherMap | Yes (free tier) | [openweathermap.org/api](https://openweathermap.org/api) |
| USGS Earthquake Hazards | No | — |
| VesselFinder | Yes (credit-based) | VesselFinder profile → API key |

Set these as environment variables or in `.streamlit/secrets.toml` rather than hardcoding them in source, e.g.:

```toml
# .streamlit/secrets.toml
OWM_API_KEY = "your-key-here"
MT_API_KEY = "your-key-here"
```

The app runs without these — live risk data is simply skipped if keys aren't configured.

## Input form

The shipment form on `app.py` collects:

- **Product profile** — category, weight, volume, handling flags (hazmat, temperature-controlled, fragile, bulk, high-value), declared value
- **Route profile** — origin/destination, distance, available infrastructure, border crossings
- **Constraints** — urgency, budget, carbon priority, schedule reliability priority, preferred/excluded modes

## License

MIT — feel free to fork and adapt.
