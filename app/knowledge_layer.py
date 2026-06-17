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
        "keywords": ["permit", "fee", "insurance", "bond", "contingency", "mobilization", "temporary", "scaffolding rental", "project management", "architect fee", "engineering fee", "superintendent", "overhead", "general conditions", "ton capacity", "concrete", "lock out", "tons radius", "entry exit", "diesel", "posts", "construction", "air", "building", "cfm", "project", "electric", "mils", "plank", "scaffolding", "aluminum", "less than", "physical search", "portable", "pump", "safety", "search entry", "see section", "self-propelled", "crane", "material", "than tall", "trailer"],
        "not": "Do not use for actual construction work — this is for soft costs and project administration only."
    },
    "2": {
        "description": "Work on existing structures: demolition, selective demolition, hazardous material abatement (asbestos, lead, mold), building deconstruction, and site clearing of existing features.",
        "keywords": ["demolish", "tear down", "remove existing", "demo", "asbestos", "lead paint", "mold remediation", "abatement", "deconstruct", "strip out", "gut", "clearance", "existing wall removal", "concrete breaking", "removal", "walls", "diameter pipe", "excludes excavation", "light", "not", "plastic", "deconstruction", "reinforcing", "brick", "hand", "metal", "floor", "frame", "masonry", "single", "duct", "gal gal", "gal tank", "interior", "materials", "natural gas", "salvage", "water", "areas", "building", "demolition", "sampling", "bituminous"],
        "not": "Not for new construction. Not for earthwork or grading — that is Division 31."
    },
    "3": {
        "description": "All concrete work: forming, reinforcing (rebar, mesh), cast-in-place concrete, precast concrete, concrete finishing, grouting, and concrete repair.",
        "keywords": ["concrete", "slab", "footing", "foundation", "rebar", "reinforcing", "formwork", "pour", "cast in place", "precast", "tilt-up", "grout", "cement", "structural slab", "column", "beam", "wall concrete", "paving concrete", "additional inch", "same hole", "reinforcing area", "core wall", "forms place", "crane bucket", "diameter core", "thickness same", "tipped legs", "epoxy", "job-built plywood", "finish", "inch depth", "see section", "welded wire", "stressing", "bar", "bull float", "dry shake", "inch slab", "precast concrete", "slab thickness", "stone", "direct chute", "form", "grit diamond", "lightweight"],
        "not": "Not for masonry block or brick (Division 4). Not for concrete paving on exterior sites (Division 32)."
    },
    "4": {
        "description": "Masonry construction: brick, concrete masonry unit (CMU) block, stone, glass block, and related mortaring and reinforcing.",
        "keywords": ["brick", "block", "CMU", "masonry", "mortar", "stone wall", "glass block", "laying brick", "block wall", "retaining wall masonry", "tuckpointing", "grout masonry", "hard mortar", "old mortar", "soft old", "concrete block", "bars", "diameter", "panels", "soil biological", "walls", "cut", "galvanized", "running bond", "corner stones", "equal", "field stones", "lightweight std", "medium price", "normal-weight psi", "plain", "black etc", "brown etc", "every course", "glazed side", "gray light"],
        "not": "Not for concrete (Division 3). Not for stone flooring or tile (Division 9)."
    },
    "5": {
        "description": "Structural and miscellaneous metals: structural steel framing, steel joists, metal decking, metal fabrications (stairs, railings, ladders), and ornamental metal.",
        "keywords": ["steel", "structural steel", "metal stud", "steel beam", "steel column", "joist", "metal deck", "railing", "stair steel", "ladder", "grating", "metal framing", "erection", "bolt", "weld", "angle iron", "made recycled", "recycled materials", "tons", "studs", "less than", "stainless steel", "squares", "framing", "shop fabricated", "plain", "bar", "metal", "than ton", "dlh", "job lots", "only", "rib", "slh", "ton job", "channel", "fancy", "concrete", "field fabricated", "joist stud", "anchors"],
        "not": "Not for light-gauge framing in walls (see Division 6). Not for metal roofing panels (Division 7)."
    },
    "6": {
        "description": "Wood and light-gauge framing, rough carpentry, finish carpentry, millwork, cabinets, casework, and composite/plastic lumber products.",
        "keywords": ["wood", "lumber", "framing", "stud wall", "joist", "plywood", "sheathing", "subfloor", "cabinet", "casework", "millwork", "trim", "molding", "wood door", "rough carpentry", "finish carpentry", "shelving", "countertop", "pneumatic nailed", "studs", "poplar", "cherry", "red oak", "diameter", "galvanized", "diam", "roof", "finger jointed", "jointed primed", "clear span", "joists", "shear", "custom", "door", "walls", "composite", "moldings", "stock pine", "blocking", "board"],
        "not": "Not for structural steel (Division 5). Not for wood flooring finishes — flooring is Division 9."
    },
    "7": {
        "description": "Building envelope protection: roofing systems, waterproofing, dampproofing, insulation (wall, roof, pipe), air/vapor barriers, caulking, sealants, and fireproofing.",
        "keywords": ["roof", "roofing", "waterproof", "insulation", "vapor barrier", "air barrier", "caulk", "sealant", "flashing", "membrane", "TPO", "EPDM", "shingles", "dampproof", "fireproof", "spray foam", "batt insulation", "rigid insulation", "gutters", "pneumatic nailed", "fiberglass", "felt mopped", "glass fiber", "panels", "wall", "galvanized steel", "accessories", "grade", "nailable decks", "face height", "joint openings", "mill finish", "pocket", "sides", "stainless steel", "base sheet", "colors", "concrete", "neoprene", "density", "depth", "exposure smooth", "fully adhered", "place"],
        "not": "Not for windows and doors (Division 8). Not for interior wall insulation cost when bundled with framing."
    },
    "8": {
        "description": "All openings in the building envelope: doors, windows, skylights, storefronts, curtain walls, glazing, and associated hardware and frames.",
        "keywords": ["door", "window", "skylight", "curtain wall", "storefront", "glass", "glazing", "frame", "hardware", "lock", "hinge", "overhead door", "garage door", "hollow metal door", "aluminum window", "entry door", "insulated glass", "stainless steel", "insul glass", "double insulated", "dbl insul", "interior", "steel base", "vinyl", "half glass", "economy", "bronze finish", "tinted", "casement", "door weighs", "exterior", "insulating glass", "black finish", "double-hung", "fixed", "heavy", "mill finish", "cut sheets", "electric", "floor"],
        "not": "Not for roofing or insulation around openings (Division 7). Interior doors without frames may still be here."
    },
    "9": {
        "description": "Interior surface finishes: drywall, plaster, tile, flooring (carpet, vinyl, wood, terrazzo), painting, wall coverings, and acoustic ceilings.",
        "keywords": ["drywall", "gypsum board", "sheetrock", "tile", "floor tile", "wall tile", "carpet", "vinyl flooring", "LVT", "paint", "painting", "acoustic ceiling", "suspended ceiling", "ceiling tile", "plaster", "terrazzo", "epoxy floor", "wall covering", "texture", "exterior latex", "primer coat", "level finish", "finish coat", "coat exterior", "primer coats", "sheets", "coat latex", "first coat", "roller", "skim coat", "thk", "coat level", "compound skim", "finished level", "second coat", "taped finished", "coat brushwork", "oil base", "both sides", "coats exterior", "brushwork primer", "cut-in brush", "metal studs", "finish cut-in"],
        "not": "Not for structural framing (Division 5 or 6). Not for exterior cladding (Division 7)."
    },
    "10": {
        "description": "Pre-manufactured specialty items: toilet partitions, lockers, fire extinguishers, signage, flagpoles, postal specialties, corner guards, and wall protection.",
        "keywords": ["toilet partition", "locker", "fire extinguisher", "sign", "signage", "flagpole", "mailbox", "corner guard", "wall protection", "shower partition", "cubicle", "whiteboard", "bulletin board", "stainless steel", "coated steel", "powder coated", "polymer plastic", "phenolic", "door frame", "doors", "handicap", "wall hung", "floor mounted", "shower", "shelf", "steel door", "truck scales", "aluminum frame", "plastic laminate", "single", "steel deck", "track", "above", "base", "cast bronze", "deck truck", "economy", "fire"],
        "not": "Not for large built-in equipment (Division 11). Not for furniture (Division 12)."
    },
    "11": {
        "description": "Built-in and specialty equipment: commercial kitchen equipment, loading dock equipment, laboratory equipment, medical equipment, and residential appliances.",
        "keywords": ["kitchen equipment", "commercial kitchen", "oven", "refrigerator", "loading dock", "dock leveler", "lab equipment", "medical equipment", "appliance", "dishwasher", "hood", "exhaust hood", "portable", "deluxe", "commercial", "stainless steel", "station", "floor", "diameter", "food", "heavy", "bottles", "ceiling", "hydraulic", "aluminum", "automatic", "dispenser", "double", "energy star", "rack", "ice", "light", "lights", "manual", "star rated", "air", "mobile"],
        "not": "Not for HVAC hoods or mechanical ventilation (Division 23). Not for furniture (Division 12)."
    },
    "12": {
        "description": "Furnishings: furniture, window treatments (blinds, shades), rugs, artwork, and built-in seating.",
        "keywords": ["furniture", "desk", "chair", "blind", "shade", "curtain", "rug", "artwork", "seating", "bench", "table", "shelving furniture", "patterned colors", "diameter", "solid colors", "stainless steel", "splash", "countertops", "drawer", "gal", "premium patterned", "square", "stock", "base cabinets", "bike cap", "built-in", "cabinet", "coat finish", "galv bike", "insert", "laminated plastic", "powder coat", "seat", "stl pipe", "vinyl"],
        "not": "Not for built-in casework or cabinets (Division 6). Not for specialties like lockers (Division 10)."
    },
    "13": {
        "description": "Non-standard and specialty construction: pre-engineered buildings, clean rooms, swimming pools, aquatic facilities, vaults, radiation shielding, and themed environments.",
        "keywords": ["pre-engineered building", "metal building", "clean room", "swimming pool", "pool", "vault", "radiation shielding", "pre-engineered", "modular building", "gunite pool", "diameter", "eave height", "panels", "diam", "floor", "door", "roof", "clear span", "stainless steel", "air", "room", "wood", "economy", "tiers seats", "bottom", "building", "class", "concrete", "copper", "plastic", "x-ray", "board", "controls", "deluxe", "mounted"],
        "not": "Not for standard building types — only highly specialized facility types."
    },
    "14": {
        "description": "Vertical and horizontal transportation: elevators, escalators, moving walks, dumbwaiters, and material lifts.",
        "keywords": ["elevator", "escalator", "lift", "moving walk", "dumbwaiter", "platform lift", "wheelchair lift", "material lift", "floor floor", "floor height", "fpm gearless", "gearless electric", "stainless steel", "fpm geared", "geared electric", "automatic controls", "car group", "group automatic", "class loading", "flooring", "base fpm", "fpm stop", "hydraulic", "increased speed", "number stops", "opening speed", "round", "speed doors", "speed fpm", "stations", "std fin", "stop std", "travel"],
        "not": "Not for mechanical equipment lifts or cranes used during construction (Division 1)."
    },
    "21": {
        "description": "Fire suppression systems: sprinkler systems (wet, dry, pre-action, deluge), fire pumps, standpipes, and specialty suppression agents.",
        "keywords": ["sprinkler", "fire suppression", "fire pump", "standpipe", "deluge", "dry pipe", "wet pipe", "halon", "clean agent", "FM-200", "fire protection piping", "agent solenoid", "cyl agent", "gpm psi", "hose", "polished brass", "polished chrome", "diameter", "valve", "container", "control", "psi pump", "sprinkler components", "valves", "double", "fittings", "flush polished", "length", "pendent", "psi rpm", "rpm pump", "single", "trim", "booster line", "dispersion nozzle"],
        "not": "Not for fire alarms and detection (Division 28). Not for fire extinguishers (Division 10)."
    },
    "22": {
        "description": "Plumbing systems: domestic water supply and distribution, sanitary waste and vent piping, storm drainage, water heaters, plumbing fixtures (sinks, toilets, tubs), and gas piping.",
        "keywords": ["plumbing", "pipe", "piping", "toilet", "sink", "lavatory", "faucet", "water heater", "drain", "waste", "vent", "water supply", "sanitary", "gas pipe", "sewer", "fixture", "water closet", "urinal", "shower", "bathtub", "hose bib", "iron pipe", "gpm discharge", "diam diam", "supply waste", "rough-in supply", "stainless steel", "waste vent", "single bowl", "valves", "cast iron", "diameter gpm", "clevis hanger", "schedule", "copper", "flanged", "wall mounted", "ada compliant", "fiberglass", "input gph", "mbh input", "bend", "floor mounted", "only", "see", "tee"],
        "not": "Not for fire suppression piping (Division 21). Not for HVAC hydronic piping (Division 23)."
    },
    "23": {
        "description": "HVAC systems: heating, ventilation, and air conditioning equipment and distribution — furnaces, boilers, chillers, cooling towers, ductwork, diffusers, terminal units (VAV, fan coil), exhaust fans, and controls.",
        "keywords": ["HVAC", "heating", "cooling", "air conditioning", "duct", "ductwork", "furnace", "boiler", "chiller", "cooling tower", "VAV", "fan coil", "rooftop unit", "RTU", "air handler", "AHU", "ventilation", "exhaust fan", "diffuser", "thermostat", "heat pump", "mini split", "split system", "mechanical", "ton cooling", "gallon capacity", "cooling mbh", "mbh output", "gpm", "hot water", "mbh heating", "flanged", "see section", "includes", "mbh heat", "cfm damper", "motor", "capacity shell", "exhaust", "insulation", "panel", "pneumatic thermostat", "roof", "water cooled", "watt", "wireless pneumatic", "air cooled", "ceiling", "centrifugal"],
        "not": "Not for plumbing (Division 22). Not for electrical power to HVAC equipment (Division 26)."
    },
    "26": {
        "description": "Electrical power systems: wiring, conduit, panels, circuit breakers, switchgear, transformers, lighting fixtures, receptacles, switches, motors, generators, and low-voltage power distribution.",
        "keywords": ["electrical", "wiring", "wire", "conduit", "panel", "circuit breaker", "outlet", "receptacle", "switch", "light", "lighting", "fixture", "LED", "transformer", "generator", "motor", "switchgear", "power", "voltage", "ampere", "feeder", "branch circuit", "service entrance", "kva", "kcmil", "kvar", "two watt", "pressure sodium", "wires", "amp main", "sodium watt", "led lamp", "lamp watts", "aluminum", "pole amp", "emt wire", "fluorescent", "main circuits", "medium base", "volt pole", "labor", "warm white", "arms", "base volt", "level", "metal halide"],
        "not": "Not for fire alarm wiring (Division 28). Not for data/telecom wiring (Division 27). Not for HVAC controls wiring (Division 23)."
    },
    "27": {
        "description": "Communications and data systems: structured cabling (Cat5e/Cat6), telephone, fiber optic, audio/visual systems, and distributed antenna systems.",
        "keywords": ["data", "cable", "network", "ethernet", "Cat6", "fiber", "telecom", "telephone", "PA system", "audio visual", "AV", "speaker", "distributed antenna", "DAS", "low voltage data", "mile range", "outlets", "master", "clock", "time", "call station", "conduits", "multi mode", "not", "panel", "rack", "single mode", "splice", "wires", "amplifier", "antenna", "bedside", "bell", "burial", "button", "cables", "cards"],
        "not": "Not for electrical power wiring (Division 26). Not for security systems (Division 28)."
    },
    "28": {
        "description": "Electronic safety and security: fire alarm systems (detection, notification), access control, video surveillance (CCTV), and intrusion detection.",
        "keywords": ["fire alarm", "smoke detector", "heat detector", "alarm", "access control", "card reader", "CCTV", "camera", "surveillance", "security system", "intrusion", "motion sensor", "panic button", "monitor", "station", "duct", "remote", "channel", "light", "adds user", "card key", "detection", "striker power", "user profiles", "video", "battery operated", "beam", "control", "door", "liquid", "monitoring", "mounted", "strobe", "vapor", "wireless"],
        "not": "Not for fire suppression (Division 21). Not for electrical power (Division 26)."
    },
    "31": {
        "description": "Earthwork and site preparation: grading, excavation, trenching, backfill, compaction, dewatering, soil stabilization, and erosion control.",
        "keywords": ["excavation", "grading", "earthwork", "cut", "fill", "backfill", "compaction", "trenching", "clearing", "grubbing", "dewatering", "soil", "earth", "grade", "erosion control", "silt fence", "topsoil", "embankment", "cycle miles", "sand gravel", "clay loam", "sandy clay", "haul sand", "see section", "bucket fill", "adverse conditions", "ideal conditions", "bell diameter", "diameter shaft", "hand", "lifts passes", "butts points", "dozer ideal", "psi rock", "cycle mile", "left place", "material", "avg cycle", "gal", "mph avg", "soil nailing", "diameter wall", "drive extract"],
        "not": "Not for site paving or curbs (Division 32). Not for underground utilities (Division 33)."
    },
    "32": {
        "description": "Exterior site improvements: paving (asphalt, concrete), curbs, sidewalks, parking lots, site lighting, landscaping, irrigation, fencing, and athletic surfaces.",
        "keywords": ["asphalt", "paving", "parking lot", "sidewalk", "curb", "gutter", "landscaping", "lawn", "irrigation", "fence", "site lighting", "striping", "retaining wall site", "athletic court", "playground", "see section", "pitting", "push spreader", "posts", "cal", "tractor spreader", "chain link", "galvanized", "air seeding", "hydro air", "small irregular", "mulch fertilizer", "seeding mulch", "irregular areas", "radius", "aluminized steel", "binder course", "conc", "rigid paving", "thermoplastic", "finish", "less than", "precast concrete", "repave cold"],
        "not": "Not for earthwork or grading (Division 31). Not for underground utilities (Division 33)."
    },
    "33": {
        "description": "Underground site utilities: water mains, sanitary sewer mains, storm sewer, gas mains, electrical ductbank, and site utility structures (manholes, catch basins).",
        "keywords": ["water main", "sewer main", "storm sewer", "utility", "underground pipe", "ductbank", "manhole", "catch basin", "fire hydrant", "gas main", "force main", "site utility", "diameter sdr", "diam pipe", "diameter pipe", "gallons", "excavation backfill", "not excavation", "diameter band", "fittings", "pipe freezing", "equivalent", "freezing side", "inlet", "kcmil", "psi coils", "basic wind", "mph basic", "service", "wind speed", "box", "ips diameter", "load mph", "wall thickness", "wind load", "butt fusion", "diameters"],
        "not": "Not for interior building plumbing (Division 22). Not for site paving (Division 32)."
    },
    "34": {
        "description": "Transportation infrastructure: roadway construction, bridges, tunnels, railroads, and transit systems.",
        "keywords": ["roadway", "bridge", "tunnel", "railroad", "rail", "transit", "highway", "pavement structure", "guardrail", "passes mph", "steel", "base housing", "relay rail", "gfrc decorative", "new rail", "ties", "track", "coat", "diam", "epoxy", "security barrier", "stl galv", "threshold", "crash barrier", "includes", "maintenance grading", "mounting base", "relay rails", "switch", "arm", "assembly", "barrier width", "bay"],
        "not": "Not for site parking lots (Division 32)."
    },
    "35": {
        "description": "Waterway and marine construction: docks, piers, bulkheads, dredging, and waterfront structures.",
        "keywords": ["dock", "pier", "bulkhead", "dredge", "marine", "waterfront", "seawall", "boat ramp", "diameter", "diam length", "square", "boat", "aluminum", "docks", "protective material", "wrap protective", "deck", "gates", "octagon", "open area", "pile", "piles straps", "shore", "steel", "treated wood", "area passes", "concrete piles", "floating", "frame", "levee", "medium"],
        "not": "Not for swimming pools (Division 13)."
    },
    "41": {
        "description": "Material processing and handling equipment: conveyors, cranes, hoists, storage systems, and industrial processing equipment.",
        "keywords": ["conveyor", "crane", "hoist", "material handling", "storage rack", "industrial equipment", "bulk material", "belt", "cranes", "length", "span ton", "lifts", "trolley", "wheel capacity", "bridge", "electric", "girder", "hoists", "horizontal", "jib", "material", "only", "overhead", "piece", "portable", "running", "track", "yard", "above", "air", "assembly"],
        "not": "Not for elevators and lifts in buildings (Division 14)."
    },
    "44": {
        "description": "Pollution and waste control equipment: air pollution control, water treatment, and waste management systems.",
        "keywords": ["pollution control", "air scrubber", "waste treatment", "environmental equipment", "filtration", "diam", "cfm inlet", "slip fit", "elbow", "vacuum", "central", "collection", "commercial", "dust", "filters", "flexible", "galvanized", "hose", "includes", "industrial", "motorized", "reinforced", "rubber", "shaker", "stand", "thru", "tubing", "wire"],
        "not": "Not for HVAC filtration in buildings (Division 23)."
    },
    "46": {
        "description": "Water and wastewater treatment equipment: pumps, tanks, filters, and treatment processes for municipal water systems.",
        "keywords": ["water treatment", "wastewater", "pump station", "filtration plant", "clarifier", "municipal water", "diameter", "amp range", "overload amp", "connection", "gpd", "cfm bhp", "aeration", "blower", "second", "mgd", "air diffuser", "not", "phase", "single", "anchoring", "check", "excluding", "filter", "freeboard", "piping", "pressure relief", "price", "relief valves", "silencer", "treatment cell"],
        "not": "Not for building plumbing (Division 22). Not for site water mains (Division 33)."
    },
    "48": {
        "description": "Electrical power generation: generators, solar panels, wind turbines, fuel cells, and co-generation systems.",
        "keywords": ["generator", "solar", "photovoltaic", "PV", "wind turbine", "fuel cell", "cogeneration", "backup power", "standby generator", "renewable energy", "uses hydrogen", "diam", "hydrogen gas", "kit", "battery", "charging", "complete", "labor", "material", "mount", "anode", "attic", "cells", "comm", "component", "components", "connected", "demonstration", "earth", "fuel", "galvanized", "grid", "guyed", "hardware", "helical"],
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


def build_root_context() -> str:
    """Return a compact reference of all divisions for level-1 selection."""
    lines = ["RSMeans Division Reference:"]
    for code, entry in DIVISION_KNOWLEDGE.items():
        keyword_sample = ", ".join(entry["keywords"])
        lines.append(f"  Div {code}: {entry['description'].split(':')[0].strip()} | keywords: {keyword_sample}")
    return "\n".join(lines)
