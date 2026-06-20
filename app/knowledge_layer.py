"""
RSMeans Knowledge Layer
Provides human-language context for each division so the AI can map
natural user queries to the correct taxonomy without guessing.

The "keywords" list of each division below is ENRICHED IN PLACE by
app/keyword_extractor.py: after the record scraper pulls the real grid
line-items for a section, the most relevant terms are appended here (deduped),
so this file always holds the full, growing vocabulary for every division.
The curated seed terms (natural/colloquial language and disambiguation hints
like "tear down", "gut") are kept and the scraped terms are added after them.
"""

DIVISION_KNOWLEDGE = {
    "1": {
        "description": "Project-level costs not tied to physical work: fees, permits, insurance, bonds, mobilization, temporary facilities, project management, and contingencies.",
        "keywords": ["permit", "fee", "insurance", "bond", "contingency", "mobilization", "temporary", "scaffolding rental", "project management", "architect fee", "engineering fee", "superintendent", "overhead", "general conditions", "concrete", "diesel", "air", "cfm", "electric", "plank", "scaffolding", "aluminum", "portable", "pump", "safety", "self-propelled", "crane", "trailer", "diameter", "tons", "truck", "mesh", "tall", "accessories", "all", "frame", "office", "post", "protection", "rental without", "roof"],
        "not": "Do not use for actual construction work — this is for soft costs and project administration only."
    },
    "2": {
        "description": "Work on existing structures: demolition, selective demolition, hazardous material abatement (asbestos, lead, mold), building deconstruction, and site clearing of existing features.",
        "keywords": ["demolish", "tear down", "remove existing", "demo", "asbestos", "lead paint", "mold remediation", "abatement", "deconstruct", "strip out", "gut", "clearance", "existing wall removal", "concrete breaking", "removal", "diameter pipe", "excludes excavation", "plastic", "deconstruction", "reinforcing", "brick", "masonry", "interior", "natural gas", "water", "demolition", "bituminous", "walls", "fence", "not", "hand", "one", "floor", "frame", "metal", "sampling", "block", "duct", "large", "salvage"],
        "not": "Not for new construction. Not for earthwork or grading — that is Division 31."
    },
    "3": {
        "description": "All concrete work: forming, reinforcing (rebar, mesh), cast-in-place concrete, precast concrete, concrete finishing, grouting, and concrete repair.",
        "keywords": ["concrete", "slab", "footing", "foundation", "rebar", "reinforcing", "formwork", "pour", "cast in place", "precast", "tilt-up", "grout", "cement", "structural slab", "column", "beam", "wall concrete", "paving concrete", "additional inch", "reinforcing area", "core wall", "crane bucket", "diameter core", "epoxy", "job-built plywood", "finish", "inch depth", "welded wire", "stressing", "bar", "bull float", "dry shake", "inch slab", "precast concrete", "slab thickness", "stone", "lightweight", "grit diamond", "min", "span kip", "bag", "brick", "extra added", "fiber", "fresh concrete", "gallon pail"],
        "not": "Not for masonry block or brick (Division 4). Not for concrete paving on exterior sites (Division 32)."
    },
    "4": {
        "description": "Masonry construction: brick, concrete masonry unit (CMU) block, stone, glass block, and related mortaring and reinforcing.",
        "keywords": ["brick", "block", "CMU", "masonry", "mortar", "stone wall", "glass block", "laying brick", "block wall", "retaining wall masonry", "tuckpointing", "grout masonry", "hard mortar", "old mortar", "concrete block", "bars", "diameter", "soil biological", "galvanized", "running bond", "glazed", "lightweight", "panels", "walls", "cut", "mix", "corner stones", "field stones", "every course", "grout reinforcing", "header every", "pink brown", "red black", "wall brick", "face brick", "brick wall", "pennsylvania", "tie"],
        "not": "Not for concrete (Division 3). Not for stone flooring or tile (Division 9)."
    },
    "5": {
        "description": "Structural and miscellaneous metals: structural steel framing, steel joists, metal decking, metal fabrications (stairs, railings, ladders), and ornamental metal.",
        "keywords": ["steel", "structural steel", "metal stud", "steel beam", "steel column", "joist", "metal deck", "railing", "stair steel", "ladder", "grating", "metal framing", "erection", "bolt", "weld", "angle iron", "recycled materials", "tons", "studs", "stainless steel", "framing", "shop fabricated", "bar", "channel", "concrete", "field fabricated", "joist stud", "anchors", "recycled", "metal", "job lots", "ton job", "composite connections", "moment composite", "paint color", "simple connections", "stories", "tread", "bracing", "curved", "diameter aluminum", "additional"],
        "not": "Not for light-gauge framing in walls (see Division 6). Not for metal roofing panels (Division 7)."
    },
    "6": {
        "description": "Wood and light-gauge framing, rough carpentry, finish carpentry, millwork, cabinets, casework, and composite/plastic lumber products.",
        "keywords": ["wood", "lumber", "framing", "stud wall", "joist", "plywood", "sheathing", "subfloor", "cabinet", "casework", "millwork", "trim", "molding", "wood door", "rough carpentry", "finish carpentry", "shelving", "countertop", "pneumatic nailed", "studs", "poplar", "cherry", "red oak", "diameter", "galvanized", "roof", "finger jointed", "jointed primed", "clear span", "joists", "shear", "custom", "door", "composite", "moldings", "stock pine", "blocking", "pine", "walls", "columns", "board"],
        "not": "Not for structural steel (Division 5). Not for wood flooring finishes — flooring is Division 9."
    },
    "7": {
        "description": "Building envelope protection: roofing systems, waterproofing, dampproofing, insulation (wall, roof, pipe), air/vapor barriers, caulking, sealants, and fireproofing.",
        "keywords": ["roof", "roofing", "waterproof", "insulation", "vapor barrier", "air barrier", "caulk", "sealant", "flashing", "membrane", "TPO", "EPDM", "shingles", "dampproof", "fireproof", "spray foam", "batt insulation", "rigid insulation", "gutters", "pneumatic nailed", "fiberglass", "glass fiber", "galvanized steel", "accessories", "mill finish", "stainless steel", "base sheet", "concrete", "neoprene", "fully adhered", "felt mopped", "panels", "wall", "nailable decks", "face height", "joint openings", "exposure smooth", "asphalt felt", "fiber felt", "joint faces", "plies glass", "aluminum cover", "blast joint"],
        "not": "Not for windows and doors (Division 8). Not for interior wall insulation cost when bundled with framing."
    },
    "8": {
        "description": "All openings in the building envelope: doors, windows, skylights, storefronts, curtain walls, glazing, and associated hardware and frames.",
        "keywords": ["door", "window", "skylight", "curtain wall", "storefront", "glass", "glazing", "frame", "hardware", "lock", "hinge", "overhead door", "garage door", "hollow metal door", "aluminum window", "entry door", "insulated glass", "stainless steel", "double insulated", "interior", "vinyl", "bronze finish", "tinted", "casement", "exterior", "insulating glass", "black finish", "double-hung", "fixed", "mill finish", "electric", "insul glass", "dbl insul", "steel base", "half glass", "acting", "commercial", "door weighs", "cut", "floor", "custom"],
        "not": "Not for roofing or insulation around openings (Division 7). Interior doors without frames may still be here."
    },
    "9": {
        "description": "Interior surface finishes: drywall, plaster, tile, flooring (carpet, vinyl, wood, terrazzo), painting, wall coverings, and acoustic ceilings.",
        "keywords": ["drywall", "gypsum board", "sheetrock", "tile", "floor tile", "wall tile", "carpet", "vinyl flooring", "LVT", "paint", "painting", "acoustic ceiling", "suspended ceiling", "ceiling tile", "plaster", "terrazzo", "epoxy floor", "wall covering", "texture", "exterior latex", "metal studs", "primer coat", "finish coat", "coat exterior", "primer coats", "coat latex", "roller", "skim coat", "coat finish", "compound skim", "finished finish", "taped finished", "coat brushwork", "oil base", "traffic", "coats exterior", "sealer coat", "brushwork primer", "paint coat", "panels", "cut-in brush", "finish cut-in", "one coat", "coats brushwork"],
        "not": "Not for structural framing (Division 5 or 6). Not for exterior cladding (Division 7)."
    },
    "10": {
        "description": "Pre-manufactured specialty items: toilet partitions, lockers, fire extinguishers, signage, flagpoles, postal specialties, corner guards, and wall protection.",
        "keywords": ["toilet partition", "locker", "fire extinguisher", "sign", "signage", "flagpole", "mailbox", "corner guard", "wall protection", "shower partition", "cubicle", "whiteboard", "bulletin board", "stainless steel", "coated steel", "powder coated", "polymer plastic", "phenolic", "door frame", "handicap", "wall hung", "floor mounted", "shower", "steel door", "truck scales", "aluminum frame", "plastic laminate", "steel deck", "cast bronze", "deck truck", "fire", "doors", "shelf", "base", "heavy-duty steel", "mesh", "metal", "partitions", "cast aluminum"],
        "not": "Not for large built-in equipment (Division 11). Not for furniture (Division 12)."
    },
    "11": {
        "description": "Built-in and specialty equipment: commercial kitchen equipment, loading dock equipment, laboratory equipment, medical equipment, and residential appliances.",
        "keywords": ["kitchen equipment", "commercial kitchen", "oven", "refrigerator", "loading dock", "dock leveler", "lab equipment", "medical equipment", "appliance", "dishwasher", "hood", "exhaust hood", "portable", "commercial", "stainless steel", "station", "diameter", "food", "bottles", "ceiling", "hydraulic", "aluminum", "dispenser", "energy star", "rack", "ice", "star rated", "air", "mobile", "wall", "arm", "floor", "energy rated", "quarts", "racks", "steam", "table", "adjustable", "bumpers"],
        "not": "Not for HVAC hoods or mechanical ventilation (Division 23). Not for furniture (Division 12)."
    },
    "12": {
        "description": "Furnishings: furniture, window treatments (blinds, shades), rugs, artwork, and built-in seating.",
        "keywords": ["furniture", "desk", "chair", "blind", "shade", "curtain", "rug", "artwork", "seating", "bench", "table", "shelving furniture", "diameter", "stainless steel", "base cabinets", "built-in", "cabinet", "laminated plastic", "powder coat", "vinyl", "patterned", "face", "splash", "countertops", "drawer", "bike cap", "coat finish", "galv bike", "insert", "seat", "stl pipe", "all", "attached backsplash", "backsplash solid", "counter"],
        "not": "Not for built-in casework or cabinets (Division 6). Not for specialties like lockers (Division 10)."
    },
    "13": {
        "description": "Non-standard and specialty construction: pre-engineered buildings, clean rooms, swimming pools, aquatic facilities, vaults, radiation shielding, and themed environments.",
        "keywords": ["pre-engineered building", "metal building", "clean room", "swimming pool", "pool", "vault", "radiation shielding", "pre-engineered", "modular building", "gunite pool", "diameter", "eave height", "door", "roof", "clear span", "stainless steel", "air", "wood", "bottom", "concrete", "copper", "plastic", "x-ray", "controls", "panels", "floor", "room", "shell", "tiers seats", "layer", "board", "shielding", "vinyl fabric", "coated", "domes"],
        "not": "Not for standard building types — only highly specialized facility types."
    },
    "14": {
        "description": "Vertical and horizontal transportation: elevators, escalators, moving walks, dumbwaiters, and material lifts.",
        "keywords": ["elevator", "escalator", "lift", "moving walk", "dumbwaiter", "platform lift", "wheelchair lift", "material lift", "floor height", "stainless steel", "automatic controls", "flooring", "hydraulic", "increased speed", "number stops", "opening speed", "speed doors", "stations", "travel", "gearless electric", "geared electric", "car group", "group controls", "loading", "base stop", "freight", "center opening", "custom model", "door", "elevators options", "emergency power", "hall", "hospital"],
        "not": "Not for mechanical equipment lifts or cranes used during construction (Division 1)."
    },
    "21": {
        "description": "Fire suppression systems: sprinkler systems (wet, dry, pre-action, deluge), fire pumps, standpipes, and specialty suppression agents.",
        "keywords": ["sprinkler", "fire suppression", "fire pump", "standpipe", "deluge", "dry pipe", "wet pipe", "halon", "clean agent", "FM-200", "fire protection piping", "hose", "polished brass", "polished chrome", "diameter", "valve", "container", "control", "sprinkler components", "valves", "fittings", "length", "pendent", "trim", "booster line", "dispersion nozzle", "agent solenoid", "cyl agent", "pump", "flush polished", "exits clng", "extinguisher", "fire extinguishing", "fog", "heads not"],
        "not": "Not for fire alarms and detection (Division 28). Not for fire extinguishers (Division 10)."
    },
    "22": {
        "description": "Plumbing systems: domestic water supply and distribution, sanitary waste and vent piping, storm drainage, water heaters, plumbing fixtures (sinks, toilets, tubs), and gas piping.",
        "keywords": ["plumbing", "pipe", "piping", "toilet", "sink", "lavatory", "faucet", "water heater", "drain", "waste", "vent", "water supply", "sanitary", "gas pipe", "sewer", "fixture", "water closet", "urinal", "shower", "bathtub", "hose bib", "iron pipe", "rough-in supply", "stainless steel", "waste vent", "single bowl", "valves", "cast iron", "clevis hanger", "schedule", "copper", "flanged", "wall mounted", "ada compliant", "fiberglass", "bend", "floor mounted", "tee", "gph", "supply waste", "bowl", "floor", "color", "thru diameter", "compartment", "couplings clevis", "elbow", "gpf", "hanger assemblies"],
        "not": "Not for fire suppression piping (Division 21). Not for HVAC hydronic piping (Division 23)."
    },
    "23": {
        "description": "HVAC systems: heating, ventilation, and air conditioning equipment and distribution — furnaces, boilers, chillers, cooling towers, ductwork, diffusers, terminal units (VAV, fan coil), exhaust fans, and controls.",
        "keywords": ["HVAC", "heating", "cooling", "air conditioning", "duct", "ductwork", "furnace", "boiler", "chiller", "cooling tower", "VAV", "fan coil", "rooftop unit", "RTU", "air handler", "AHU", "ventilation", "exhaust fan", "diffuser", "thermostat", "heat pump", "mini split", "split system", "mechanical", "ton cooling", "gpm", "hot water", "flanged", "motor", "exhaust", "insulation", "panel", "pneumatic thermostat", "roof", "water cooled", "watt", "wireless pneumatic", "air cooled", "ceiling", "centrifugal", "cooling heating", "includes", "thru", "cooling heat", "package", "tube", "gallon shell", "flow", "packaged", "stainless steel"],
        "not": "Not for plumbing (Division 22). Not for electrical power to HVAC equipment (Division 26)."
    },
    "26": {
        "description": "Electrical power systems: wiring, conduit, panels, circuit breakers, switchgear, transformers, lighting fixtures, receptacles, switches, motors, generators, and low-voltage power distribution.",
        "keywords": ["electrical", "wiring", "wire", "conduit", "panel", "circuit breaker", "outlet", "receptacle", "switch", "light", "lighting", "fixture", "LED", "transformer", "generator", "motor", "switchgear", "power", "voltage", "ampere", "feeder", "branch circuit", "service entrance", "kva", "kcmil", "kvar", "pressure sodium", "wires", "led lamp", "aluminum", "emt wire", "fluorescent", "main circuits", "medium base", "warm white", "metal halide", "wall", "surface", "ceiling", "labor", "arms", "face", "frame", "primary secondary", "cable tray", "circuit breakers", "conduit wire", "four", "halogen", "led warm"],
        "not": "Not for fire alarm wiring (Division 28). Not for data/telecom wiring (Division 27). Not for HVAC controls wiring (Division 23)."
    },
    "27": {
        "description": "Communications and data systems: structured cabling (Cat5e/Cat6), telephone, fiber optic, audio/visual systems, and distributed antenna systems.",
        "keywords": ["data", "cable", "network", "ethernet", "Cat6", "fiber", "telecom", "telephone", "PA system", "audio visual", "AV", "speaker", "distributed antenna", "DAS", "low voltage data", "call station", "conduits", "multi mode", "panel", "rack", "single mode", "splice", "wires", "amplifier", "antenna", "bedside", "bell", "burial", "button", "cables", "mile range", "outlets", "master", "clock", "time", "not", "cards", "ceiling"],
        "not": "Not for electrical power wiring (Division 26). Not for security systems (Division 28)."
    },
    "28": {
        "description": "Electronic safety and security: fire alarm systems (detection, notification), access control, video surveillance (CCTV), and intrusion detection.",
        "keywords": ["fire alarm", "smoke detector", "heat detector", "alarm", "access control", "card reader", "CCTV", "camera", "surveillance", "security system", "intrusion", "motion sensor", "panic button", "monitor", "station", "remote", "channel", "adds user", "card key", "detection", "striker power", "user profiles", "video", "battery operated", "beam", "control", "door", "liquid", "monitoring", "strobe", "vapor", "wireless", "duct", "wall", "additional"],
        "not": "Not for fire suppression (Division 21). Not for electrical power (Division 26)."
    },
    "31": {
        "description": "Earthwork and site preparation: grading, excavation, trenching, backfill, compaction, dewatering, soil stabilization, and erosion control.",
        "keywords": ["excavation", "grading", "earthwork", "cut", "fill", "backfill", "compaction", "trenching", "clearing", "grubbing", "dewatering", "soil", "earth", "grade", "erosion control", "silt fence", "topsoil", "embankment", "soil nailing", "sand gravel", "clay loam", "sandy clay", "haul sand", "bucket fill", "adverse conditions", "ideal conditions", "bell diameter", "diameter shaft", "hand", "butts points", "dozer ideal", "hauling", "diameter wall", "extract salvage", "mobilization demobilization", "removal", "sheeting", "borrow", "hard dozer", "large", "mesh", "proctor", "site"],
        "not": "Not for site paving or curbs (Division 32). Not for underground utilities (Division 33)."
    },
    "32": {
        "description": "Exterior site improvements: paving (asphalt, concrete), curbs, sidewalks, parking lots, site lighting, landscaping, irrigation, fencing, and athletic surfaces.",
        "keywords": ["asphalt", "paving", "parking lot", "sidewalk", "curb", "gutter", "landscaping", "lawn", "irrigation", "fence", "site lighting", "striping", "retaining wall site", "athletic court", "playground", "pitting", "push spreader", "tractor spreader", "chain link", "galvanized", "air seeding", "hydro air", "small irregular", "mulch fertilizer", "seeding mulch", "irregular areas", "radius", "aluminized steel", "binder course", "rigid paving", "thermoplastic", "finish", "precast concrete", "repave cold", "span", "cal", "conc", "surface patch", "clay", "crushed stone", "galv steel"],
        "not": "Not for earthwork or grading (Division 31). Not for underground utilities (Division 33)."
    },
    "33": {
        "description": "Underground site utilities: water mains, sanitary sewer mains, storm sewer, gas mains, electrical ductbank, and site utility structures (manholes, catch basins).",
        "keywords": ["water main", "sewer main", "storm sewer", "utility", "underground pipe", "ductbank", "manhole", "catch basin", "fire hydrant", "gas main", "force main", "site utility", "diameter sdr", "diameter pipe", "gallons", "excavation backfill", "diameter band", "fittings", "pipe freezing", "equivalent", "freezing side", "inlet", "kcmil", "basic wind", "service", "wind speed", "box", "ips diameter", "wall thickness", "butt fusion", "diameters", "not excavation", "lengths", "outlets", "end cap", "transformers", "wind basic", "cts diameter", "handling spotting", "septic tanks", "elbows diameter", "galvanized", "gas", "sewage"],
        "not": "Not for interior building plumbing (Division 22). Not for site paving (Division 32)."
    },
    "34": {
        "description": "Transportation infrastructure: roadway construction, bridges, tunnels, railroads, and transit systems.",
        "keywords": ["roadway", "bridge", "tunnel", "railroad", "rail", "transit", "highway", "pavement structure", "guardrail", "steel", "new rail", "ties", "coat", "epoxy", "security barrier", "threshold", "crash barrier", "maintenance grading", "switch", "assembly", "base housing", "relay rail", "end", "gfrc decorative", "cross ties", "face", "pressure treated", "stl galv", "timber switch", "includes", "mounting base", "relay rails", "sliding", "arm", "barrier width", "bay"],
        "not": "Not for site parking lots (Division 32)."
    },
    "35": {
        "description": "Waterway and marine construction: docks, piers, bulkheads, dredging, and waterfront structures.",
        "keywords": ["dock", "pier", "bulkhead", "dredge", "marine", "waterfront", "seawall", "boat ramp", "diameter", "boat", "aluminum", "docks", "protective material", "wrap protective", "deck", "gates", "octagon", "open area", "pile", "shore", "steel", "treated wood", "concrete piles", "floating", "levee", "length", "clay", "piles straps", "frame", "miles", "restricted area", "slope area"],
        "not": "Not for swimming pools (Division 13)."
    },
    "41": {
        "description": "Material processing and handling equipment: conveyors, cranes, hoists, storage systems, and industrial processing equipment.",
        "keywords": ["conveyor", "crane", "hoist", "material handling", "storage rack", "industrial equipment", "bulk material", "belt", "cranes", "length", "lifts", "trolley", "bridge", "electric", "girder", "hoists", "horizontal", "jib", "overhead", "piece", "portable", "running", "yard", "air", "assembly", "span ton", "wheel", "beam", "box", "cantilever", "cap"],
        "not": "Not for elevators and lifts in buildings (Division 14)."
    },
    "44": {
        "description": "Pollution and waste control equipment: air pollution control, water treatment, and waste management systems.",
        "keywords": ["pollution control", "air scrubber", "waste treatment", "environmental equipment", "filtration", "elbow", "vacuum", "central", "collection", "commercial", "dust", "filters", "flexible", "galvanized", "hose", "industrial", "motorized", "reinforced", "rubber", "shaker", "stand", "tubing", "wire", "inlet", "slip fit", "includes", "thru"],
        "not": "Not for HVAC filtration in buildings (Division 23)."
    },
    "46": {
        "description": "Water and wastewater treatment equipment: pumps, tanks, filters, and treatment processes for municipal water systems.",
        "keywords": ["water treatment", "wastewater", "pump station", "filtration plant", "clarifier", "municipal water", "diameter", "connection", "gpd", "aeration", "blower", "second", "mgd", "air diffuser", "phase", "anchoring", "check", "excluding", "filter", "freeboard", "piping", "pressure relief", "relief valves", "silencer", "overload range", "not", "cell excluding", "treatment cell", "wafer style", "wastewater treatment", "aerator", "aerators", "anchors", "backfill", "blowers"],
        "not": "Not for building plumbing (Division 22). Not for site water mains (Division 33)."
    },
    "48": {
        "description": "Electrical power generation: generators, solar panels, wind turbines, fuel cells, and co-generation systems.",
        "keywords": ["generator", "solar", "photovoltaic", "PV", "wind turbine", "fuel cell", "cogeneration", "backup power", "standby generator", "renewable energy", "battery", "charging", "mount", "anode", "attic", "cells", "component", "components", "connected", "demonstration", "earth", "fuel", "galvanized", "grid", "guyed", "hardware", "helical", "uses hydrogen", "hydrogen gas", "kit", "labor", "comm", "installed", "inverter", "mounting"],
        "not": "Not for building electrical distribution (Division 26)."
    },
}


def get_division_context(division_code: str) -> str:
    """Return a formatted context string for a specific division."""
    entry = DIVISION_KNOWLEDGE.get(str(division_code))
    if not entry:
        return ""
    lines = [
        f"Division {division_code} covers: {entry['description']}",
        f"Common user terms: {', '.join(entry['keywords'])}",
        f"Note: {entry['not']}"
    ]
    return "\n".join(lines)


def formatting_guidance() -> dict:
    """
    How a user should phrase a cost question. Returned to the user whenever a
    request is too ambiguous to route, so they learn to ask correctly rather
    than being handed a silent guess.
    """
    return {
        "how_to_ask": (
            "Describe a single line item as an action plus the material or "
            "item, e.g. 'Cost to [install/replace/repair/paint/pour] a "
            "[material or item] [size/type/location]'."
        ),
        "rules": [
            "Always name the specific material or item (this matters most).",
            "Ask about one line item per question — not several at once.",
            "Add a qualifier when it helps: size, type, interior/exterior, residential/commercial.",
            "Everyday words are fine — you do not need RSMeans codes.",
        ],
        "good_examples": [
            "Cost to paint interior walls",
            "Install a 200 amp electrical panel",
            "Replace a residential water heater",
            "Pour a 4 inch concrete slab",
        ],
        "avoid_examples": [
            "Tell me the cost  (no item named)",
            "How much will it cost?  (nothing to look up)",
            "Paint walls and install outlets  (two trades at once)",
        ],
    }


def build_root_context() -> str:
    """Return a compact reference of all divisions for level-1 selection."""
    lines = ["RSMeans Division Reference:"]
    for code, entry in DIVISION_KNOWLEDGE.items():
        keyword_sample = ", ".join(entry["keywords"])
        lines.append(f"  Div {code}: {entry['description'].split(':')[0].strip()} | keywords: {keyword_sample}")
    return "\n".join(lines)
