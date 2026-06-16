# Transport Advisor — Logistics Decision Tool

## Project structure
```
logistics_tool/
├── app.py            ← Input form (this step)
├── engine.py         ← Decision engine (next step)
└── README.md
```

## How to run

```bash
pip install streamlit
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## What the input form collects

### 1. Product profile
- Category (perishable, hazmat, bulk, etc.)
- Weight (kg) and volume (m³)
- Special handling flags: hazmat, temperature-controlled, fragile, bulk, high-value
- Temperature range (if cold chain needed)
- Declared value (USD)

### 2. Route profile
- Origin and destination (country + city)
- Distance (km) — auto-banded into Local / Regional / Long-haul / Intercontinental
- Infrastructure available at destination (sea / air / rail / road)
- Number of border crossings

### 3. Constraints
- Urgency (Not urgent → Critical)
- Max freight budget (USD)
- Carbon footprint priority
- Schedule reliability priority
- Preferred / excluded modes

## Output (next step)
On submit, the form produces a structured JSON payload passed to `engine.py`,
which scores and recommends transport modes.
