"""
handling_instructions.py
────────────────────────
Generates detailed, product- and mode-specific transport and storage
instructions for a given shipment payload and recommended mode.

Returns a structured dict with sections:
  packaging        — container type, inner packaging, cushioning
  labelling        — required marks, UN numbers, certificates
  temperature      — range, humidity, breach consequences
  stacking         — max layers, orientation, load limits
  storage          — warehouse type, shelf life, incompatibles
  monitoring       — what to check, how often, who is responsible
  documentation    — required paperwork per mode and route
  mode_specific    — handling notes specific to the transport mode
  regulatory       — permits, regulations, compliance bodies
"""

# ═══════════════════════════════════════════════════════════════════════════════
# BASE INSTRUCTION LIBRARY  (category → section → instructions)
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_INSTRUCTIONS: dict[str, dict] = {

    "Perishable goods (food/pharma)": {
        "packaging": [
            "Use insulated packaging (EPS foam, vacuum-insulated panels, or PCM gel packs) rated for the full journey duration plus 30% buffer.",
            "Inner product must be sealed in food-grade or pharma-grade primary packaging (vacuum-sealed pouches, blister packs, or sealed vials).",
            "Place gel packs or dry ice around — not directly on — product to prevent freeze burns.",
            "Secondary packaging must be leak-proof and moisture-resistant (poly-lined corrugated boxes or Styrofoam containers).",
            "Master carton should be double-walled corrugated (minimum BCT 5 kN) and strapped with polyester banding.",
        ],
        "labelling": [
            "Mark all surfaces: 'PERISHABLE — KEEP REFRIGERATED', temperature range, and 'DO NOT FREEZE' if applicable.",
            "Include product description, batch/lot number, expiry date, and country of origin on each carton.",
            "Food products: attach phytosanitary certificate, health certificate, and fumigation certificate on outside of package.",
            "Pharmaceutical: attach Certificate of Analysis (CoA), GDP compliance statement, and cold chain log holder.",
            "Use internationally recognised temperature indicator labels (e.g. TempTale, Sensitech) visible on the outside.",
        ],
        "temperature": [
            "Frozen goods: maintain −18°C or below at all times. Any excursion above −12°C for >2 hours is cause for rejection.",
            "Chilled goods: maintain 2°C–8°C. Excursions above 15°C for >30 minutes require quality assessment.",
            "Pharma cold chain (2°C–8°C): log every 15 minutes using calibrated data loggers; provide full temperature history at delivery.",
            "Humidity: keep below 65% RH for most food products; pharma typically requires 40%–60% RH.",
            "Do not pre-cool packaging in a warm room — always cool the packaging and product together.",
        ],
        "stacking": [
            "Maximum 3 layers of master cartons unless structural testing confirms higher stacking strength.",
            "Orient cartons with arrows ('This Way Up') strictly followed — misorientation causes liquid migration.",
            "Do not place heavy non-perishable cargo on top of perishable boxes.",
            "Palletise using cold-storage pallets; wrap with stretch film to stabilise but allow air circulation.",
        ],
        "storage": [
            "Dedicated cold store or refrigerated warehouse; no co-storage with non-food chemicals.",
            "FIFO (First In, First Out) rotation strictly enforced.",
            "Minimum 30 cm clearance from walls and ceiling for air circulation.",
            "Temperature-controlled loading docks required — cargo must not sit at ambient temperature >15 minutes during transfer.",
            "Record all cold store entry/exit times and temperatures in the cold chain log.",
        ],
        "monitoring": [
            "Continuous temperature data logging throughout transit (minimum 15-minute intervals).",
            "Data logger must be pre-calibrated, activated before packing, and downloaded at destination.",
            "Designate a cold chain manager responsible for monitoring real-time alerts.",
            "At each handover point (origin warehouse → carrier → port/airport → destination warehouse), record temperature and cargo condition.",
            "Immediate escalation protocol if temperature breach is detected: contact shipper and consignee within 1 hour.",
        ],
        "documentation": [
            "Commercial invoice with HS code, declared value, and detailed product description.",
            "Packing list with net/gross weight per carton and total.",
            "Health certificate issued by competent authority (e.g. FSSAI for India, FDA for US).",
            "Phytosanitary certificate for plant-based products.",
            "Certificate of Origin.",
            "Cold chain temperature log (historical and projected).",
            "For pharmaceutical: GDP certificate, batch release certificate, import permit at destination.",
        ],
        "regulatory": [
            "Food: comply with CODEX Alimentarius standards; destination country food safety regulations apply.",
            "Pharma: comply with WHO GDP guidelines, EU GDP Directive 2013/C 343/01, or 21 CFR Part 211 (US).",
            "Meat/dairy: typically requires import permits, veterinary health certificates, and pre-approval by destination authority.",
            "Organic certified products: maintain chain-of-custody documentation throughout.",
        ],
    },

    "Hazardous materials": {
        "packaging": [
            "Use UN-certified packaging — packaging type (1A1, 4G, etc.) must match the hazard class and packing group.",
            "Packing Group I (highest danger): use maximum strength UN packaging with inner/outer cushioning.",
            "Packing Group II/III: standard UN-certified packaging; follow manufacturer's compatibility guidelines.",
            "Liquids: include absorbent material sufficient to absorb the full contents in case of leakage.",
            "Outer packaging must be able to withstand 1.5× the contents' vapour pressure in the worst-case transit temperature.",
        ],
        "labelling": [
            "Affix correct GHS/hazard class diamond labels on at least two opposite sides of each package.",
            "Mark UN number, proper shipping name, packing group, and emergency contact number (24-hr).",
            "'KEEP AWAY FROM HEAT', 'FLAMMABLE', 'CORROSIVE', or class-specific warnings as required.",
            "IMDG/ADR/IATA labels must be in English plus destination country language.",
            "Emergency Response Guide (ERG) number must be referenced on shipping documents.",
        ],
        "temperature": [
            "Flammables: store and transport below flash point − 10°C wherever possible.",
            "Temperature-sensitive hazmat (e.g. organic peroxides): follow manufacturer's specified temperature range exactly.",
            "Never store near heat sources, direct sunlight, or in ambient temperature that could cause pressure build-up.",
            "Refrigerated hazmat: ensure refrigerant itself is compatible with the hazmat (e.g. liquid nitrogen with cryogenic materials).",
        ],
        "stacking": [
            "Segregate by hazard class — consult IMDG/IATA segregation tables before co-loading.",
            "Liquids must never be stacked above solids.",
            "Limit stacking height to manufacturer's specification or maximum 2 layers for heavy drums.",
            "Oxidisers must not be placed near flammables — maintain minimum 3 m separation.",
        ],
        "storage": [
            "Dedicated hazmat store with appropriate containment bunding (110% of largest container volume).",
            "Ventilation: forced ventilation to prevent vapour accumulation (minimum 10 air changes/hour for flammables).",
            "No smoking, open flames, or ignition sources within 10 m of flammable hazmat.",
            "Fire suppression system (sprinkler or CO₂) appropriate for the hazard class.",
            "Incompatible classes must be physically separated — refer to IMDG segregation chart.",
            "24-hour access-controlled storage with CCTV monitoring.",
        ],
        "monitoring": [
            "Regular visual inspection for leaks, corrosion, or label damage during transit.",
            "Gas detectors required in enclosed storage areas for flammable or toxic vapours.",
            "Emergency spill kit and PPE must accompany the shipment.",
            "Driver/crew must be trained in emergency response for the specific hazard class.",
            "Regular check of containment integrity at each loading/unloading point.",
        ],
        "documentation": [
            "Dangerous Goods Declaration (DGD) — mandatory for all modes.",
            "Material Safety Data Sheet (MSDS / SDS) — one copy per consignment, one at origin, one at destination.",
            "Transport Emergency Card (TREMCARD) for road transport.",
            "IMDG Dangerous Goods Manifest for sea freight.",
            "Shipper's Declaration for Dangerous Goods (IATA Form) for air freight.",
            "Emergency contact details (24-hour) on all documents.",
            "Special permit or exemption certificate if applicable.",
        ],
        "regulatory": [
            "Road: ADR (Europe), HMVR (India), DOT 49 CFR (USA).",
            "Sea: IMDG Code (International Maritime Dangerous Goods).",
            "Air: IATA Dangerous Goods Regulations (DGR) — updated annually.",
            "Rail: RID regulations (Europe).",
            "Import/export permit may be required for controlled substances, explosives, or dual-use chemicals.",
            "Carrier must be licensed to transport the specific hazard class.",
        ],
    },

    "Live animals": {
        "packaging": [
            "Use IATA Live Animals Regulations (LAR)-compliant containers — container must allow ventilation on all sides.",
            "Container size: animal must be able to stand, turn around, and lie down naturally.",
            "Non-absorbent, leak-proof floor with sufficient bedding material (wood shavings, straw as appropriate).",
            "Food and water containers must be accessible from outside without opening the unit.",
            "Label 'LIVE ANIMALS' on all sides in red letters minimum 25 mm high.",
        ],
        "labelling": [
            "'LIVE ANIMALS — THIS WAY UP' arrows on all four sides.",
            "Species name (common and Latin), number of animals, sex, age, and weight on the label.",
            "Emergency contact for the owner/shipper (24-hour).",
            "Feeding/watering instructions on the outside of the container.",
            "CITES permit number (if applicable) on all documents and container.",
        ],
        "temperature": [
            "Maintain species-appropriate temperature at all times — consult veterinarian for exact ranges.",
            "Tropical species: minimum 20°C; arctic species: maximum 10°C.",
            "Avoid direct air conditioning vents blowing on the container.",
            "Temperature during loading/unloading must not deviate >5°C from optimal range.",
        ],
        "stacking": [
            "NEVER stack other cargo on top of live animal containers.",
            "Predator species must not be placed adjacent to prey species.",
            "Maintain visual barriers between naturally antagonistic species.",
            "Secure containers to prevent shifting — animals may destabilise loose containers.",
        ],
        "storage": [
            "Animals must not be held in cargo sheds longer than necessary — maximum holding times per IATA LAR.",
            "Access to food and water every 4 hours for most mammals; follow IATA LAR for species-specific intervals.",
            "Veterinary inspection at origin and, if required, at destination port.",
            "Climate-controlled animal holding area if transit >4 hours.",
        ],
        "monitoring": [
            "Visual welfare check every 4 hours minimum during transit.",
            "Log feeding, watering, and any unusual behaviour or health observations.",
            "Airline/carrier must have trained animal handlers on staff.",
            "Immediate veterinary contact protocol if animal shows distress.",
        ],
        "documentation": [
            "CITES permit (Convention on International Trade in Endangered Species) if species is listed.",
            "Veterinary health certificate issued within 10 days of departure.",
            "IATA Live Animals Regulations checklist completed by shipper.",
            "Import/export permit from both origin and destination countries.",
            "Quarantine clearance at destination (may require pre-arranged quarantine facility).",
            "Acclimatisation certificate if animals have been in captivity.",
        ],
        "regulatory": [
            "IATA Live Animals Regulations (LAR) — mandatory for air transport.",
            "CITES for internationally traded species.",
            "Destination country import permit and quarantine requirements.",
            "EU: Council Regulation (EC) No 1/2005 on protection of animals during transport.",
            "India: PCA Act, Wildlife Protection Act, DAHD guidelines.",
        ],
    },

    "Oversized / heavy machinery": {
        "packaging": [
            "Heavy machinery should be cleaned and dried before packing to prevent corrosion during transit.",
            "Coat exposed metal surfaces with rust-inhibiting grease or VCI (Volatile Corrosion Inhibitor) film.",
            "Block and brace all moving parts (arms, blades, wheels) to prevent movement-induced damage.",
            "Use custom-built wooden crates (ISPM 15 heat-treated timber) for full enclosure.",
            "Foam, bubble wrap, or rubber pads on contact points between machine and crate walls.",
        ],
        "labelling": [
            "Mark centre of gravity (CoG) on all four sides — critical for lifting operations.",
            "Sling/lifting points marked with yellow paint or stencil.",
            "Maximum stack height: '1 HIGH — DO NOT STACK'.",
            "Gross weight and dimensions on all sides (tonne and metres).",
            "Operating instructions or setup notes enclosed inside waterproof sleeve on package.",
        ],
        "temperature": [
            "Hydraulic systems: protect from extreme cold (below −10°C) as seals may crack.",
            "Electronic control units: maintain above 0°C and below 45°C.",
            "Apply desiccant sachets inside enclosed packaging to prevent moisture condensation.",
        ],
        "stacking": [
            "Project cargo: do not stack unless engineering calculation confirms structural capacity.",
            "Use spreader beams for wide lifts to distribute load evenly.",
            "Flat-rack or open-top containers for sea; low-loader or step-frame trailer for road.",
            "Confirm bridge/tunnel clearances on road route before dispatch.",
        ],
        "storage": [
            "Hard-standing storage area (concrete or compacted gravel) — not soft ground.",
            "Covered storage preferred; if outdoor, use waterproof tarpaulin with ventilation gaps.",
            "Do not store near corrosive chemicals or saltwater exposure without protection.",
            "Monthly inspection of packaging integrity and corrosion protection.",
        ],
        "monitoring": [
            "Escort vehicle required for loads exceeding road width/weight limits (rules vary by country).",
            "Police notification and permits for abnormal loads.",
            "Real-time GPS tracking on the prime mover.",
            "Lashing inspection at every rest stop (minimum every 250 km).",
        ],
        "documentation": [
            "Commercial invoice with HS code and detailed machine description.",
            "Packing list with dimensions (L×W×H) and weight.",
            "Abnormal load permit from transport authorities of each country transited.",
            "Lifting plan and rigging chart from certified rigger.",
            "Insurance certificate covering full replacement value.",
            "Phytosanitary treatment certificate for wooden packaging (ISPM 15).",
        ],
        "regulatory": [
            "Road: Abnormal Indivisible Load (AIL) permit from each country's road authority.",
            "Sea: IMO guidelines for project cargo; LOL (Letter of Lashing) from marine surveyor.",
            "Port terminals: advance notification and booking of heavy-lift crane if required.",
            "Customs: may require pre-import registration in destination country.",
        ],
    },

    "High-value goods (electronics/jewellery)": {
        "packaging": [
            "Use rigid, tamper-evident packaging with serialised security seals on all openings.",
            "Electronics: antistatic bags (ESD) as inner packaging; foam-in-place or custom-cut foam inserts.",
            "Jewellery/precious metals: individual pouches in padded compartments; do not rattle.",
            "Double-box method: product in inner box, inner box cushioned within outer box, minimum 5 cm padding on all sides.",
            "Unmarked outer packaging — avoid branding that advertises high value.",
        ],
        "labelling": [
            "Outer carton should be plain or use generic description (e.g. 'Electronic Components') — avoid 'Jewellery' or 'Gold'.",
            "Serial numbers and security seal numbers recorded on internal packing list (not visible externally).",
            "Handling instructions: 'FRAGILE — HANDLE WITH CARE', 'KEEP DRY'.",
            "Reference number only on outside (no product value stated on exterior).",
        ],
        "temperature": [
            "Electronics: store and transport between 0°C and 40°C; avoid condensation (RH < 60%).",
            "LCD screens and batteries: avoid temperatures below −20°C or above 60°C.",
            "Jewellery: no specific temperature limits, but avoid extremes that may affect gemstone adhesives or settings.",
            "Desiccant sachets in all packages to prevent moisture damage to electronics.",
        ],
        "stacking": [
            "Maximum 2 layers for electronics — never place heavy cargo on top.",
            "Orient 'THIS WAY UP' strictly — inverted electronics packaging voids many warranties.",
            "Use pallets with corner protectors; wrap with stretch film for stability.",
        ],
        "storage": [
            "Secure, access-controlled warehouse with CCTV — minimum 24-hour footage retention.",
            "Inventory reconciliation at each handover — piece count must match documents.",
            "Temperature and humidity controlled storage for electronics.",
            "Jewellery/precious metals: bank-grade vault or bonded warehouse with armed security.",
        ],
        "monitoring": [
            "GPS tracking device inside the shipment (concealed) for real-time location monitoring.",
            "Chain-of-custody signature required at every handover.",
            "Tamper-evident seal numbers logged and verified at destination.",
            "Insure for full replacement value — confirm carrier liability limits (often far below declared value).",
        ],
        "documentation": [
            "Commercial invoice with itemised list, serial numbers, and declared value.",
            "Packing list with security seal numbers.",
            "Insurance certificate for full CIF (Cost, Insurance, Freight) value.",
            "For jewellery/precious metals: export licence from origin country; import permit at destination.",
            "For electronics with encryption: may require export licence under EAR (US) or similar.",
            "Certificate of authenticity for branded goods.",
        ],
        "regulatory": [
            "Precious metals and gemstones: Kimberley Process Certification (diamonds), CITES (coral, ivory).",
            "Electronics: export control regulations (EAR, ITAR for US-origin dual-use tech).",
            "Customs: accurate HS code and valuation mandatory — undervaluation is a criminal offence.",
            "CE marking / FCC certification may be required for electronics in destination market.",
        ],
    },

    "Bulk commodities (grain/coal/ore)": {
        "packaging": [
            "Typically transported unpackaged in bulk — vessel holds, bulk rail wagons, or bulk truck bodies.",
            "If bagged: use heavy-duty woven polypropylene bags (50 kg standard), heat-sealed or sewn tops.",
            "Jumbo bags (FIBCs): minimum SWL 1,000 kg, UN-certified for hazardous bulk powders.",
            "Grain: fumigation of holds/containers before loading to prevent pest infestation.",
        ],
        "labelling": [
            "Bill of Lading description must state exact commodity, moisture content, and grade.",
            "Vessel/wagon identification at loading point.",
            "Bagged commodities: weight, grade, origin, and lot number on each bag.",
            "Hazardous bulk (coal, sulphur): IMDG bulk labels and EmS codes on manifest.",
        ],
        "temperature": [
            "Grain: moisture content must be below 14% before loading to prevent spoilage and spontaneous heating.",
            "Coal: monitor temperature during long voyages — spontaneous combustion risk if moisture >8% and fine content high.",
            "Iron ore: can liquefy if moisture content exceeds Transportable Moisture Limit (TML) — test before loading.",
            "Fertilisers: keep dry and away from heat; ammonium nitrate has strict temperature and separation requirements.",
        ],
        "stacking": [
            "Bulk: loaded by conveyor, grab, or pneumatic pump — stacking not applicable.",
            "Bagged: maximum 10 layers on pallets; ensure bag integrity before stacking.",
            "Coal and concentrates: slope angle of cargo in holds must not exceed angle of repose.",
        ],
        "storage": [
            "Open-yard storage acceptable for coal and ore; covered shed required for grain.",
            "Grain: silo storage preferred; regular aeration and temperature monitoring to prevent hot spots.",
            "Commodity separation: do not store grain near chemicals, fertilisers, or fuels.",
            "Regular stock rotation and inspection for moisture ingress or pest activity.",
        ],
        "monitoring": [
            "Moisture content testing at origin and destination (independent surveyor recommended).",
            "Draft survey at loading and discharge to verify quantity.",
            "Continuous temperature monitoring for coal (spontaneous combustion risk).",
            "Independent cargo surveyor at both ends for high-value bulk shipments.",
        ],
        "documentation": [
            "Bill of Lading or Consignment Note.",
            "Certificate of Weight / Draft Survey Report.",
            "Certificate of Quality / Grade Certificate from accredited lab.",
            "Moisture Content Certificate (especially for ores and concentrates).",
            "Phytosanitary certificate for grain and agricultural bulk.",
            "Fumigation certificate (grain).",
            "For coal: Certificate of Origin and Coal Quality Analysis.",
        ],
        "regulatory": [
            "IMSBC Code (International Maritime Solid Bulk Cargoes) for sea transport.",
            "Grain: USDA FGIS, GAFTA, or equivalent origin certification.",
            "Fertilisers with ammonium nitrate: UN classification 5.1, strict IMDG requirements.",
            "Destination country phytosanitary requirements for agricultural bulk.",
        ],
    },

    "Liquid bulk (chemicals/fuel)": {
        "packaging": [
            "Transported in ISO tank containers, flexitanks, or IBC (Intermediate Bulk Containers) depending on volume.",
            "ISO tank: material compatibility must be verified — stainless steel 316L for most chemicals.",
            "Flexitank: single-use, food-grade for non-hazardous liquids (wine, edible oils); maximum 24,000 litres.",
            "IBC: UN-certified for hazardous liquids; inspect for corrosion and valve integrity before use.",
            "All fittings, valves, and manhole covers must be leak-tested before departure.",
        ],
        "labelling": [
            "Placard hazard class, UN number, and emergency contact on all four sides of tank.",
            "Previous cargo label must be removed or crossed out completely.",
            "Fill level indicator and maximum gross weight on tank.",
            "Emergency Response Guidebook number on documents.",
        ],
        "temperature": [
            "Heated tanks required for viscous liquids (bitumen, heavy oils) — specify heating medium and temperature.",
            "Cryogenic liquids (LNG, liquid nitrogen): use vacuum-insulated cryogenic ISO tanks; strict pressure monitoring.",
            "Chemical tanks: avoid temperature extremes that may cause polymerisation, crystallisation, or decomposition.",
        ],
        "stacking": [
            "ISO tanks: maximum 2 high when stacked (verify structural rating).",
            "IBC: do not stack unless specifically rated — check manufacturer's stacking load.",
            "Never drive vehicles over IBCs or flexitank-fitted containers.",
        ],
        "storage": [
            "Bunded area with capacity for 110% of largest tank volume.",
            "Separate storage for acids, alkalis, oxidisers, and flammables — consult compatibility matrix.",
            "Earthing/bonding connections for flammable liquid tanks.",
            "No ignition sources within 15 m of flammable liquid storage.",
        ],
        "monitoring": [
            "Pressure and temperature gauges monitored continuously for cryogenics and reactive chemicals.",
            "Sample analysis at origin and destination for product quality verification.",
            "Heel inspection (residue from previous cargo) before loading.",
            "Independent surveyor for quantity measurement at load and discharge.",
        ],
        "documentation": [
            "Dangerous Goods Declaration (for hazardous).",
            "Tank Certificate (last inspection date, test pressure).",
            "Certificate of Analysis (CoA) for chemical quality.",
            "Previous cargo certificate.",
            "Safety Data Sheet (SDS).",
            "Customs import/export declaration with HS code.",
        ],
        "regulatory": [
            "IMDG Code for sea; ADR for road; RID for rail.",
            "Tank must have current CSC (Container Safety Convention) plate.",
            "Periodic inspection certificate (ISO tank: 2.5-year and 5-year intervals).",
            "Environmental liability insurance for chemical spills.",
        ],
    },

    "Medical / pharmaceutical": {
        "packaging": [
            "Primary packaging must be pharma-grade (USP/EP compliant): blister packs, ampoules, sealed vials.",
            "Secondary packaging: tamper-evident, moisture-resistant cartons with serialisation (track-and-trace).",
            "Cold-chain shipper validated for the required temperature profile (2°C–8°C or −20°C, etc.).",
            "Packaging must be validated for the worst-case transit duration plus 50% buffer.",
            "Include calibrated temperature data logger (pre-activated) inside each outer shipper.",
        ],
        "labelling": [
            "Batch number, expiry date, storage conditions, and regulatory approval number on every unit.",
            "'STORE BETWEEN 2°C–8°C', 'DO NOT FREEZE', 'PROTECT FROM LIGHT' as applicable.",
            "Controlled substance: additional security labels and restricted-access documentation.",
            "Track-and-trace serial number (GS1 standard) on each carton for supply chain visibility.",
            "Multi-language labelling if required by destination country regulations.",
        ],
        "temperature": [
            "Cold chain (2°C–8°C): any excursion above 15°C for >30 minutes triggers quarantine and quality review.",
            "Frozen (−20°C or −80°C): use dry ice (sublimation rate ~5 kg/24 hrs/box) or LN₂ dry shippers for ultra-cold.",
            "CRT (Controlled Room Temperature, 15°C–25°C): protect from freezing and direct sunlight.",
            "Mean Kinetic Temperature (MKT) calculation may be required for excursions — consult QA.",
        ],
        "stacking": [
            "Pharmaceutical shippers: do not stack — marked '1 HIGH' or 'DO NOT STACK'.",
            "If palletised: use rigid transit trays between shipper layers; maximum 2 layers.",
            "Segregate from non-pharma cargo in the hold/truck to prevent cross-contamination risk.",
        ],
        "storage": [
            "GDP-compliant warehouse: temperature-mapped, access-controlled, with written SOPs.",
            "Quarantine area for incoming goods until quality release by QA team.",
            "Controlled substances: double-locked, access-restricted, with register of access.",
            "Ambient, refrigerated, and frozen zones clearly segregated with no cross-access.",
            "Backup power supply (UPS/generator) for refrigerated areas mandatory.",
        ],
        "monitoring": [
            "Continuous temperature monitoring with remote alarm system (SMS/email alert for breach).",
            "Data logger downloaded and reviewed at every handover — records submitted to QA.",
            "Calibrated monitoring equipment — calibration certificate renewed annually.",
            "Named qualified person (QP or RP) responsible for cold chain at each handover.",
        ],
        "documentation": [
            "GDP-compliant packing list and airway bill / Bill of Lading.",
            "Certificate of Analysis (CoA) and Certificate of Compliance (CoC).",
            "Import/export licence (especially for controlled substances, biologics, vaccines).",
            "WHO Health Certificate or Free Sale Certificate for finished products.",
            "Temperature excursion report form (pre-prepared, to be completed at destination if needed).",
            "Controlled drugs: narcotics licence, import authorisation from destination MOH.",
        ],
        "regulatory": [
            "WHO Good Distribution Practice (GDP) guidelines.",
            "EU GDP Directive (2013/C 343/01) for European distribution.",
            "US FDA 21 CFR Parts 210/211 for US-origin or US-bound pharma.",
            "ICH Q1A–Q1F stability guidelines for temperature-sensitive products.",
            "Controlled substances: UN Convention on Narcotic Drugs, local MOH import authorisation.",
        ],
    },

    "E-commerce parcels": {
        "packaging": [
            "Use right-sized boxes — dimensional weight (DIM weight) charges apply for air and courier.",
            "Fill void space with air pillows, crinkle paper, or biodegradable peanuts.",
            "Fragile items: minimum 5 cm cushioning on all sides; wrap individually in bubble wrap.",
            "Poly mailers acceptable for non-fragile, non-liquid items under 2 kg.",
            "Resealable or easy-open packaging improves customer experience and reduces returns damage.",
        ],
        "labelling": [
            "Shipping label must include: sender, recipient, tracking barcode, service level, and weight.",
            "HS code and customs value declaration on international shipments.",
            "Battery labels (UN 3481, UN 3091) if lithium batteries included — check airline acceptance.",
            "'FRAGILE', 'THIS WAY UP', 'KEEP DRY' labels as appropriate.",
        ],
        "temperature": [
            "Most e-commerce: no special temperature requirements — store and ship at ambient.",
            "Cosmetics and some health products: avoid prolonged exposure above 35°C or below 0°C.",
            "Batteries: do not expose to temperatures above 60°C (fire risk).",
        ],
        "stacking": [
            "Lightweight parcels: machine-sortable if within courier dimensional limits.",
            "Fragile parcels: mark clearly; hand-sort required — request 'fragile handling' service.",
            "Do not place heavy parcels on top of fragile ones.",
        ],
        "storage": [
            "Fulfilment warehouse: ambient, clean, dry, pest-controlled.",
            "FIFO rotation for perishable or time-sensitive e-commerce products.",
            "Returns area segregated from outbound inventory.",
        ],
        "monitoring": [
            "End-to-end tracking via courier API — provide tracking number to customer at dispatch.",
            "Exception alerts for failed delivery attempts, customs holds, or damage reports.",
            "Returns monitoring: 30-day return rate tracked by SKU.",
        ],
        "documentation": [
            "Customs declaration (CN22 or CN23 for international postal; commercial invoice for courier).",
            "HS code and accurate value declaration — low-value de minimis thresholds vary by country.",
            "Battery declaration if lithium batteries included.",
            "Certificate of Origin if preferential tariff claimed.",
        ],
        "regulatory": [
            "Lithium batteries: IATA PI 966/967/968/969/970 depending on type and state (standalone, in device).",
            "Destination country import threshold (de minimis): below this value, no customs duty.",
            "GDPR / data protection: customer data on shipping labels must be handled compliantly.",
            "Prohibited items list: each courier and country has its own list — check before accepting.",
        ],
    },

    "Automotive parts": {
        "packaging": [
            "Engine and drivetrain components: drain all fluids before packing; seal openings with plugs.",
            "Sheet metal and body panels: interleave with foam or felt to prevent scratch damage.",
            "Electrical components: use antistatic packaging (ESD bags) for ECUs, sensors, and wiring harnesses.",
            "Tyres: stack horizontally (maximum 4 high); do not stack with other cargo on top.",
            "Glass (windscreens): vertical orientation in A-frames with rubber separation between panes.",
        ],
        "labelling": [
            "Part number, OEM code, vehicle model compatibility, and batch number on each unit.",
            "Hazardous components (batteries, airbag inflators): appropriate hazmat labels and UN numbers.",
            "Country of origin marking required for customs (stamped or labelled on part).",
        ],
        "temperature": [
            "Rubber seals and gaskets: avoid temperatures below −30°C or above 50°C.",
            "Batteries (12V lead-acid or lithium): follow battery-specific temperature requirements.",
            "Electronic parts: keep between 0°C and 40°C; avoid condensation.",
        ],
        "stacking": [
            "Heavy components (engines, gearboxes): wooden crated, single layer, bottom-loaded in container.",
            "Sheet metal: vertical in purpose-built A-frame racks inside container.",
            "Mixed auto parts containers: heaviest items floor-level, fragile items top-loaded.",
        ],
        "storage": [
            "Covered, dry warehouse; rubber and plastic components away from UV light and ozone sources.",
            "Battery storage: ventilated area; lead-acid batteries separated from other cargo.",
            "Bin location system for small parts; racking for crated components.",
        ],
        "monitoring": [
            "Inventory reconciliation at receipt against packing list — automotive JIT supply chains have zero tolerance for discrepancy.",
            "Quality inspection for damage at delivery — claim window with carrier is often <7 days.",
        ],
        "documentation": [
            "Commercial invoice with part numbers, OEM codes, and HS codes.",
            "Certificate of Origin (preferential tariff agreements e.g. ASEAN FTA, EU-India when applicable).",
            "Packing list.",
            "Dangerous goods declaration for airbag modules (UN 0503) or lithium batteries.",
        ],
        "regulatory": [
            "Airbag inflators: Class 1.4G explosive — restricted on passenger aircraft, full DG compliance on cargo aircraft.",
            "Used parts: may require import permits and duty treatment different from new parts.",
            "Country-specific type approval or homologation may be required for safety-critical parts.",
        ],
    },

    "Garments & textiles": {
        "packaging": [
            "Hang-garments: use garment bags on hanging rails in specially equipped 'garment-on-hanger' (GOH) containers.",
            "Folded garments: polybag each piece individually; pack in export cartons by SKU.",
            "Desiccant sachets in each carton to prevent mould and mildew during humid sea transit.",
            "Master carton: minimum double-wall corrugated; strapped or banded for stability.",
            "Delicate fabrics (silk, cashmere): tissue paper wrapping before polybag.",
        ],
        "labelling": [
            "Carton label: SKU, style number, size range, quantity, colour, and destination.",
            "Country of origin label on each garment (sewn-in label) — mandatory for customs.",
            "Care instructions label on each garment per destination country requirements (ASTM D5489 for US, ISO 3758 for EU).",
            "Carton sequence number for easy unpacking at destination (carton 1 of N).",
        ],
        "temperature": [
            "Avoid temperatures above 35°C — heat can cause dye bleeding or fabric damage.",
            "GOH containers: ensure adequate ventilation to prevent condensation on fabrics.",
            "Wool and natural fibres: desiccant essential for humidity control; target RH below 60%.",
        ],
        "stacking": [
            "Folded garment cartons: maximum 8 layers; do not compress delicate fabrics.",
            "GOH containers: hanging rails must be secured; do not overload — allow 5 cm between garments.",
        ],
        "storage": [
            "Cool, dry, dark warehouse — UV light causes fading in many dyes.",
            "Pest control (moths, silverfish) essential for natural fibre storage.",
            "FIFO rotation especially important for fashion with seasonal sell-by dates.",
        ],
        "monitoring": [
            "Random quality audit (AQL inspection) at origin and destination.",
            "Check for mould, odour, or colour transfer on arrival — common after long humid sea transit.",
        ],
        "documentation": [
            "Commercial invoice with HS code (Chapter 61/62), unit price, and country of origin.",
            "Packing list with detailed breakdown by carton, SKU, size, and quantity.",
            "Certificate of Origin (preferential if applicable).",
            "Test reports for restricted substances (REACH, OEKO-TEX, CPSC for children's garments).",
            "For US: Textile Fiber Products Identification Act (TFPIA) compliance.",
        ],
        "regulatory": [
            "EU: REACH regulation on restricted substances in textiles.",
            "US: CPSC flammability standards for children's sleepwear.",
            "Country of origin marking mandatory in most markets.",
            "Anti-dumping duties may apply for certain origin/destination pairs — check tariff schedule.",
        ],
    },

    "General cargo": {
        "packaging": [
            "Use appropriate carton strength for the weight: <10 kg = single wall; 10–25 kg = double wall; >25 kg = triple wall or wooden crate.",
            "Inner contents must not shift — fill voids with packing material.",
            "Seal all seams with water-activated tape or 50 mm pressure-sensitive tape.",
            "Palletise where possible using standard 1200×1000 mm EUR or 1200×800 mm pallets.",
        ],
        "labelling": [
            "Shipping label on at least two sides: sender, recipient, weight, and dimensions.",
            "Handling labels as needed: 'FRAGILE', 'THIS WAY UP', 'KEEP DRY'.",
            "For international: commercial value and HS code on customs invoice.",
        ],
        "temperature": [
            "Standard ambient storage (15°C–30°C) for most general cargo.",
            "Avoid prolonged exposure to direct sunlight, moisture, or extreme cold for sensitive goods.",
        ],
        "stacking": [
            "Heaviest cartons at the bottom of the stack.",
            "Maximum stack height should not exceed the structural limit printed on carton (BCT value).",
            "Use corner boards for extra stacking stability on palletised cargo.",
        ],
        "storage": [
            "Dry, covered warehouse with pest control.",
            "Leave aisle access of minimum 1 m for forklift and inspection.",
            "Secure valuable general cargo in caged or locked storage area.",
        ],
        "monitoring": [
            "Count and condition check at every handover.",
            "Photograph cargo before sealing for insurance evidence.",
        ],
        "documentation": [
            "Commercial invoice.",
            "Packing list.",
            "Bill of Lading (sea) or Airway Bill (air) or Consignment Note (road).",
            "Certificate of Origin if required at destination.",
        ],
        "regulatory": [
            "ISPM 15 heat treatment for wooden packaging on international shipments.",
            "Customs: accurate HS code and declared value on all international documents.",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# MODE-SPECIFIC OVERLAYS
# ═══════════════════════════════════════════════════════════════════════════════

MODE_OVERLAYS: dict[str, list[str]] = {
    "Air freight": [
        "All packages must comply with IATA Cargo Regulations — dimensions and weight per ULD or general cargo limits.",
        "Lithium batteries: separate declaration required (IATA PI 965–970); quantity limits per package apply.",
        "Screened cargo programme: shipper must be IATA CCSF-approved or cargo subject to physical security screening.",
        "Air waybill (AWB) required — one master AWB per shipment; house AWBs for consolidated cargo.",
        "Dangerous goods must have airline-specific approval before booking — not all carriers accept all DG classes.",
        "Temperature-sensitive cargo: book on direct or minimal-connection routings; specify 'cold chain required' at booking.",
        "Cargo must be at airport cargo terminal minimum 3–4 hours before scheduled departure.",
    ],
    "Sea freight (FCL)": [
        "Full Container Load (FCL): shipper is responsible for packing and sealing the container.",
        "Verify container condition (CSC plate, door seals, floor integrity, no odours) before loading — use a pre-trip inspection (PTI) checklist.",
        "Lash and secure cargo within container using dunnage bags, wooden bracing, or lashing straps.",
        "VGM (Verified Gross Mass) declaration mandatory under SOLAS — submit to carrier before CY cut-off.",
        "Customs Entry must be lodged in destination country before vessel arrival in most jurisdictions.",
        "Reefer containers: verify power supply at terminal; set temperature before loading; monitor via carrier's reefer tracking portal.",
        "Container seal number must match the Bill of Lading exactly — discrepancy causes customs delay.",
    ],
    "Sea freight (LCL)": [
        "Less than Container Load (LCL): cargo consolidated at origin CFS (Container Freight Station) with other shippers' goods.",
        "Additional handling at CFS increases risk of damage — ensure robust packaging and 'FRAGILE' labels where relevant.",
        "Transit time includes deconsolidation at destination CFS — add 3–7 days to port-to-port transit.",
        "LCL cargo is typically insured per consignment — declare full value to consolidator.",
        "Do not ship hazardous cargo LCL unless consolidator has DG-certified CFS facility.",
        "Cargo receipt (CFS receipt) must be obtained and checked against packing list at origin CFS.",
    ],
    "Road freight": [
        "Cargo securing is the driver's and shipper's joint responsibility — comply with EN 12195 (Europe) or equivalent.",
        "Lashing calculation: total lashing force must equal or exceed cargo weight × friction coefficient.",
        "For cross-border road: CMR Consignment Note required (Europe); ensure original accompanies the vehicle.",
        "Tachograph compliance: driver hours must comply with EC 561/2006 (EU) or equivalent national rules.",
        "Temperature-controlled road: verify refrigeration unit pre-trip; record temperatures at loading, mid-transit, and delivery.",
        "GPS tracking recommended — provides proof of delivery time and route compliance.",
        "Confirm vehicle dimensions and weight comply with regulations on each country of transit.",
    ],
    "Rail freight": [
        "Cargo must be loaded and secured per UIC (International Union of Railways) loading guidelines.",
        "Centre of gravity must be within the wagon's permissible limits — asymmetric loads require calculation.",
        "CIM Consignment Note for international rail freight (COTIF convention).",
        "Rail offers limited handling flexibility at intermediate points — confirm origin and destination siding or terminal access.",
        "Temperature-controlled rail: limited availability; confirm reefer wagon availability with operator well in advance.",
        "China-Europe rail (Belt and Road): gauge change at Kazakhstan/Poland border — factor in transfer time.",
        "Customs transit declarations required for each country crossed — use TIR carnet or NCTS where applicable.",
    ],
    "Multimodal": [
        "Single multimodal transport document (MTD) covers the entire journey — issued by MTO (Multimodal Transport Operator).",
        "Packing must withstand multiple loading/unloading cycles — more handovers mean more handling risk.",
        "Ensure packaging and labelling is compatible with all modes in the chain (e.g. sea-rated and road-rated).",
        "Liability regime changes at each mode — the MTO assumes overall liability but claims may involve multiple carriers.",
        "Track and trace: use a single tracking number provided by the MTO that covers all legs.",
        "Customs transit procedure must cover all borders — multimodal operators typically handle this as part of the service.",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# FLAG-SPECIFIC ADDITIONS
# ═══════════════════════════════════════════════════════════════════════════════

FLAG_ADDITIONS: dict[str, dict[str, list[str]]] = {
    "temperature_controlled": {
        "monitoring": [
            "Activate data logger minimum 30 minutes before packing to confirm it is functioning.",
            "Set alarm thresholds 2°C tighter than product specification to catch drift before breach.",
        ],
        "documentation": [
            "Cold chain qualification report for the shipping lane (PPQ or TSE study).",
            "Temperature excursion investigation form — to be completed if any alarm fires.",
        ],
    },
    "hazmat": {
        "packaging": [
            "UN certification number must be embossed or permanently marked on each package.",
        ],
        "documentation": [
            "Emergency response telephone number (24-hour) mandatory on all transport documents.",
            "Multimodal Dangerous Goods Form if more than one mode is used.",
        ],
    },
    "fragile": {
        "packaging": [
            "Double-box method mandatory: product in inner box (with 5 cm cushioning), inner box inside outer box (with 5 cm cushioning).",
            "Drop test packaging to ASTM D4169 or ISTA 2A before use for high-value fragile items.",
        ],
        "stacking": [
            "Mark '1 HIGH — DO NOT STACK' on all outer cartons.",
        ],
    },
    "high_value": {
        "storage": [
            "Insure for full replacement value — note that most carrier standard liability is capped at ~USD 20/kg.",
        ],
        "monitoring": [
            "Covert GPS tracker inside shipment (battery life minimum = journey duration + 7 days).",
            "Named security escort for road transport of very high-value goods (>USD 500,000).",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

SECTION_TITLES = {
    "packaging":     "📦 Packaging requirements",
    "labelling":     "🏷️ Labelling & markings",
    "temperature":   "🌡️ Temperature & humidity",
    "stacking":      "📐 Stacking & load rules",
    "storage":       "🏭 Storage conditions",
    "monitoring":    "📡 In-transit monitoring",
    "documentation": "📋 Documentation checklist",
    "regulatory":    "⚖️ Regulatory compliance",
    "mode_specific": "🚀 Mode-specific handling",
}


def get_instructions(payload: dict, best_mode: str) -> dict[str, list[str]]:
    """
    Returns a dict of section_key → [instruction strings]
    combining base category instructions, mode overlays, and flag additions.
    """
    category = payload.get("product", {}).get("category", "General cargo")
    flags    = payload.get("product", {}).get("flags", [])

    # Start with base category
    base = CATEGORY_INSTRUCTIONS.get(category, CATEGORY_INSTRUCTIONS["General cargo"])
    result: dict[str, list[str]] = {k: list(v) for k, v in base.items()}

    # Add mode-specific overlay
    result["mode_specific"] = MODE_OVERLAYS.get(best_mode, [])

    # Add flag-specific additions
    for flag in flags:
        additions = FLAG_ADDITIONS.get(flag, {})
        for section, items in additions.items():
            if section not in result:
                result[section] = []
            result[section] = result[section] + items

    return result


def get_section_title(key: str) -> str:
    return SECTION_TITLES.get(key, key.replace("_", " ").title())
