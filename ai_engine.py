import re

# ── Issue patterns (v1 — keep exactly) ────────────────────────────────────────

ISSUE_PATTERNS = [
    # (name, keywords, weight)
    ("demand decline",          ["drop", "decline", "decrease", "fall", "no sales", "low sales", "revenue down", "sales down", "losing customers", "losing clients", "revenue fell"], 3),
    ("customer dissatisfaction",["complaint", "bad review", "dissatisfied", "unhappy", "angry", "refund", "churn", "negative feedback", "poor service", "bad experience", "terrible service"], 2),
    ("operational inefficiency",["delay", "slow", "bottleneck", "backlog", "stuck", "process", "inefficient", "overdue", "manual", "rework", "delivery time", "taking too long", "delivery", "shipping time", "response time", "wait time"], 2),
    ("inefficient marketing",   ["marketing", "ads", "spend", "cac", "roas", "campaign", "no leads", "low conversion", "traffic", "acquisition cost", "ad spend"], 1),
    ("financial pressure",      ["profit", "loss", "cost", "budget", "expense", "not profitable", "losing money", "underfunded", "in the red", "margins"], 2),
    ("cash flow issue",         ["cash", "burn", "runway", "invoice", "payable", "receivable", "liquidity", "overdraft", "out of money", "can't pay"], 3),
    ("talent retention",        ["resign", "quit", "turnover", "attrition", "hire", "staff leaving", "team leaving", "employee left", "people leaving", "losing people"], 2),
    ("product quality issue",   ["bug", "quality", "defect", "broken", "not working", "malfunction", "failure", "crash", "recall", "error", "poor product"], 2),
    ("competitive pressure",    ["competitor", "competition", "market share", "losing to", "undercutting", "price war", "outcompeted", "losing deals", "rival"], 2),
    ("scaling bottleneck",      ["scale", "capacity", "infrastructure", "overwhelmed", "can't handle", "growing too fast", "volume", "growth is outpacing", "growing fast", "growing quickly", "rapid growth"], 2),
    ("leadership misalignment", ["direction", "vision", "conflict", "executives", "leadership disagree", "strategy unclear", "no clear plan", "management conflict", "no alignment"], 2),
    ("compliance or legal risk",["legal", "compliance", "regulation", "penalty", "fine", "audit", "lawsuit", "tax issue", "liability", "gdpr", "notice"], 3),
]

URGENCY_CRITICAL = ["shutdown", "bankrupt", "closing", "lawsuit", "emergency", "crisis", "collapse", "dire", "catastrophic", "zero runway"]
URGENCY_HIGH     = ["urgent", "asap", "this week", "quickly", "serious", "major", "escalating", "worsening", "immediately", "right now", "today"]
URGENCY_LOW      = ["thinking about", "considering", "planning for", "eventually", "long term", "someday", "in the future"]

# ── Industry signals ───────────────────────────────────────────────────────────

INDUSTRY_SIGNALS = {
    "saas": [
        "saas", "subscription", "mrr", "arr", "churn rate", "monthly recurring", "annual recurring",
        "software as a service", "b2b software", "product-led", "freemium", "seat", "license",
        "trial conversion", "upsell", "expansion revenue",
    ],
    "d2c": [
        "d2c", "direct to consumer", "dtc", "shopify", "ecommerce", "e-commerce", "online store",
        "brand", "instagram", "influencer", "repurchase", "aov", "average order value",
        "repeat purchase", "paid social", "facebook ads", "meta ads",
    ],
    "retail": [
        "retail", "store", "shop", "foot traffic", "pos", "point of sale", "inventory", "shelf",
        "stockout", "merchandising", "brick and mortar", "mall", "outlet", "retail chain",
        "same store sales", "comparable sales",
    ],
    "logistics": [
        "logistics", "freight", "shipping", "delivery", "fleet", "driver", "route", "warehouse",
        "fulfilment", "fulfillment", "last mile", "cargo", "dispatch", "3pl", "supply chain",
        "courier", "transit time",
    ],
    "fintech": [
        "fintech", "payments", "lending", "credit", "loan", "wallet", "neobank", "banking",
        "transaction", "interchange", "underwriting", "kyc", "aml", "regtech", "nbfc",
        "financial services", "remittance", "insurance",
    ],
    "healthtech": [
        "healthtech", "health tech", "healthcare", "hospital", "clinic", "patient", "telemedicine",
        "telehealth", "ehr", "emr", "medical", "pharma", "drug", "therapy", "diagnosis",
        "health insurance", "health data",
    ],
    "edtech": [
        "edtech", "education", "learning", "course", "student", "teacher", "school", "university",
        "tutoring", "lms", "curriculum", "enrolment", "enrollment", "cohort", "bootcamp",
        "e-learning", "online learning",
    ],
    "marketplace": [
        "marketplace", "platform", "two-sided", "seller", "buyer", "gig", "freelance",
        "take rate", "gmv", "gross merchandise", "listing", "supply side", "demand side",
        "liquidity", "match rate", "transaction volume",
    ],
    "manufacturing": [
        "manufacturing", "factory", "production", "plant", "assembly", "oem", "sku",
        "yield", "defect rate", "throughput", "capacity utilisation", "capacity utilization",
        "procurement", "raw material", "supplier", "batch", "tooling",
    ],
}

# ── Company stage signals ──────────────────────────────────────────────────────

COMPANY_STAGE_SIGNALS = {
    "startup": [
        "seed", "pre-seed", "series a", "mvp", "idea stage", "early stage", "pre-revenue",
        "founded", "co-founder", "founder", "just launched", "launch", "bootstrap",
        "first customers", "product-market fit", "runway", "angel",
    ],
    "growth": [
        "series b", "series c", "scaling", "growing fast", "hypergrowth", "rapid growth",
        "expanding", "hiring quickly", "new markets", "international", "vc-backed",
        "venture funded", "100 employees", "50 employees", "200 employees",
    ],
    "sme": [
        "sme", "small business", "medium business", "family business", "owner operated",
        "10 years", "15 years", "20 years", "established", "profitable", "cash generative",
        "no investors", "self-funded", "local", "regional",
    ],
    "enterprise": [
        "enterprise", "large company", "public company", "listed", "fortune", "multinational",
        "global", "thousands of employees", "corporate", "division", "business unit",
        "cfo", "coo", "board", "shareholders", "quarterly earnings", "p&l owner",
    ],
}

# ── Hypothesis trees removed — now live in knowledge/docs/frameworks/*.md ──────
# Retrieval pulls the relevant framework at query time instead.

_REMOVED_HYPOTHESIS_TREES = {
    "demand decline": [
        "Is the demand decline concentrated in a specific channel, region, or customer segment — or is it broad-based across all revenue streams?",
        "Has the competitive landscape shifted — new entrant, price cut, or product launch — that is diverting our target customers?",
        "Is there a product-market fit deterioration: did our core offer stop solving the problem it used to solve?",
        "Did an internal change — pricing, sales coverage, or marketing spend reduction — trigger the volume drop?",
    ],
    "customer dissatisfaction": [
        "Is the dissatisfaction concentrated in a specific product, touchpoint, or customer segment — or is it systemic across the entire journey?",
        "Has a recent change — product update, policy shift, team restructure — created a new failure point in the customer experience?",
        "Is the gap between customer expectation and actual delivery driven by overpromising in marketing and sales?",
        "Are frontline staff equipped and empowered to resolve issues at the point of contact, or are they escalating everything?",
    ],
    "operational inefficiency": [
        "Where exactly in the value chain is the highest concentration of delay, rework, or cost — and is that the true binding constraint or a symptom?",
        "Is the inefficiency driven by process design (the workflow itself is broken) or execution (the process exists but is not followed)?",
        "Are we carrying excess capacity, redundant steps, or manual handoffs that automation or redesign could eliminate?",
        "Does the team lack the skills, tools, or decision authority to execute efficiently at their level?",
    ],
    "inefficient marketing": [
        "Is underperformance concentrated in specific channels, creatives, or audiences — or is overall market demand declining?",
        "Is our attribution model correctly capturing the contribution of each channel, or are we making budget decisions on incomplete data?",
        "Has creative fatigue, audience saturation, or platform algorithm changes degraded performance that was previously strong?",
        "Is the conversion failure happening at the ad level, landing page, or post-lead handoff to sales?",
    ],
    "financial pressure": [
        "Is the margin compression driven by rising input costs, falling revenue, or a structural shift in the business model?",
        "Which specific cost lines are growing faster than revenue — and are they fixed or variable?",
        "Is there a single product line, geography, or customer segment that is structurally unprofitable and dragging the blended margin down?",
        "Are pricing decisions being made with full visibility of true unit economics, including all direct and allocated costs?",
    ],
    "cash flow issue": [
        "Is the cash shortfall caused by timing mismatches (receivables vs. payables cycles) or by an underlying profitability problem?",
        "Which customers account for the largest outstanding receivables, and what is blocking their payment?",
        "Are there non-core assets, excess inventory, or prepaid commitments that can be converted to cash quickly?",
        "What is the true minimum operating cash requirement per week, and how many weeks of runway remain at current burn?",
    ],
    "talent retention": [
        "Is attrition concentrated in specific teams, tenure bands, or roles — or is it spread across the organisation?",
        "Are departing employees leaving for better compensation, better growth opportunities, or a better culture — and which factor dominates?",
        "Is the manager layer the common denominator in high-attrition teams — poor management is the single biggest driver of voluntary exit?",
        "Has the company's mission, pace, or work environment shifted in a way that no longer attracts or retains the original talent profile?",
    ],
    "product quality issue": [
        "Is the defect or quality failure driven by a design flaw, a manufacturing or engineering process failure, or a supplier quality issue?",
        "Is this a regression — something that was working and has broken — or a gap that was never caught in initial QA?",
        "What is the failure rate, and is it concentrated in a specific batch, cohort, or configuration?",
        "Does the QA process have the right gates, test coverage, and escalation authority to catch issues before they reach customers?",
    ],
    "competitive pressure": [
        "Is the competitor winning on price alone, or have they made a genuine product, distribution, or brand move that changes the value equation?",
        "Which customer segments are most at risk of switching, and which are the most loyal — and why?",
        "Do we have a genuinely defensible moat (switching costs, network effect, proprietary data, brand) or are we competing on features that can be copied?",
        "Is the competitive threat from an existing player escalating, or a new entrant disrupting the category from below?",
    ],
    "scaling bottleneck": [
        "What is the single binding constraint — people, technology, process, or capital — and at what volume does it break?",
        "Is the constraint in the core delivery mechanism, or in support functions (onboarding, billing, compliance) that slow down the customer journey?",
        "Are we trying to scale a process that is fundamentally not scalable without redesign, or just under-resourced?",
        "Do we have sufficient lead time to relieve the constraint before current demand growth hits the ceiling?",
    ],
    "leadership misalignment": [
        "Is the disagreement about strategic direction (where to compete), resource allocation (how to prioritise), or execution accountability (who owns what)?",
        "Is this a new conflict triggered by a specific event — funding round, key hire, board pressure — or a long-standing cultural pattern?",
        "Does the organisation have a clear decision-making framework, or do major decisions require unanimous consensus that never comes?",
        "Is the misalignment contained to the executive team, or has it already cascaded into team-level confusion and conflicting priorities?",
    ],
    "compliance or legal risk": [
        "Is the exposure driven by a gap in current compliance processes, a change in regulation that has not yet been addressed, or a historical practice now under scrutiny?",
        "What is the maximum financial and operational penalty if the current exposure becomes a formal regulatory action?",
        "Do we have internal counsel with the relevant regulatory expertise, or do we need specialist external counsel immediately?",
        "Is this risk isolated to one jurisdiction, product, or business line — or does it require a company-wide remediation programme?",
    ],
}

# ── Industry benchmarks removed — now live in knowledge/docs/benchmarks/*.md ───
# Retrieval pulls relevant benchmarks at query time instead.

_REMOVED_INDUSTRY_BENCHMARKS = {
    "saas": [
        "Best-in-class SaaS net revenue retention (NRR) is 120%+; below 100% means the base is shrinking even before new sales.",
        "Healthy SaaS CAC payback period is under 12 months; above 18 months signals a broken unit economics model.",
        "Top-quartile SaaS gross margins run 75–85%; below 60% suggests infrastructure or service delivery costs are too high.",
        "SaaS churn above 2% monthly (24% annually) is structurally unsustainable and requires immediate root cause analysis.",
        "Rule of 40: growth rate + EBITDA margin should exceed 40% for a healthy SaaS business at scale.",
    ],
    "d2c": [
        "D2C brands with healthy unit economics target a contribution margin of 30–40% after paid acquisition costs.",
        "Average D2C customer repurchase rate benchmarks at 25–35% for consumables; below 15% signals weak product-market retention.",
        "ROAS of 2–4x is typical for paid social at scale; below 1.5x means you are buying revenue at a loss.",
        "D2C customer acquisition cost has risen 60–70% over 5 years — brands dependent on paid social face structural margin pressure.",
        "Top-performing D2C brands drive 30%+ of revenue from repeat customers within 12 months of launch.",
    ],
    "retail": [
        "Retail gross margins range from 30–50% for general merchandise; below 25% leaves insufficient room for operating expenses.",
        "Inventory turnover of 4–6x per year is healthy for most retail categories; below 3x signals overbuying or demand issues.",
        "Shrinkage (theft + admin error) above 1.5% of sales is a material problem requiring loss-prevention investment.",
        "Same-store sales growth of 3–5% annually is considered healthy for established retail; flat or negative signals a structural issue.",
        "Labour cost as a percentage of sales should be 15–20% for most retail formats; above 25% indicates overstaffing or productivity gaps.",
    ],
    "logistics": [
        "On-time delivery rates below 95% create compounding customer dissatisfaction and claims costs that erode margin.",
        "Fleet utilisation below 75% is a major inefficiency driver; idle assets are one of logistics' largest avoidable costs.",
        "Fuel cost typically represents 25–35% of logistics operating cost — hedging or route optimisation is critical.",
        "Customer damage and loss claims above 0.5% of shipment value signals packaging, handling, or loading process failures.",
        "Last-mile delivery accounts for 40–50% of total logistics cost and is the primary lever for both cost and customer experience.",
    ],
    "marketplace": [
        "Marketplace take rates typically range from 10–30%; below 10% makes unit economics very difficult at moderate GMV.",
        "Healthy marketplace liquidity requires a match rate (searches resulting in transactions) above 60% for core categories.",
        "Supplier/seller concentration: if top 20% of sellers drive 80%+ of GMV, platform risk is high if those sellers churn.",
        "Marketplace NPS above 50 for both buyer and seller sides is needed to sustain organic growth and resist platform substitution.",
        "Monthly active user (MAU) to transaction conversion above 15% is considered strong for transactional marketplaces.",
    ],
    "manufacturing": [
        "Overall Equipment Effectiveness (OEE) above 85% is world-class; below 60% signals significant production losses.",
        "Defect rate (parts per million / PPM) targets vary by industry but above 500 PPM is a quality flag for most precision manufacturing.",
        "Capacity utilisation of 80–85% is the optimal range; above 90% risks quality and maintenance failure; below 70% means excess fixed cost.",
        "Inventory carrying cost is typically 20–30% of inventory value per year — excess WIP and finished goods are a direct cash drain.",
        "Supplier on-time-in-full (OTIF) rate below 90% creates cascading production schedule disruptions and should trigger dual-sourcing.",
    ],
    "fintech": [
        "Credit loss rates (net charge-offs) above 3–5% of loan book for consumer lending indicate underwriting model failure.",
        "Payment processing uptime below 99.95% creates material customer and merchant trust damage in regulated environments.",
        "KYC/AML false positive rates above 10% create operational drag and customer friction without improving risk outcomes.",
        "Customer acquisition cost in fintech ranges $100–500 for consumer products; above $500 requires strong LTV justification.",
        "Regulatory capital adequacy ratios must be maintained above minimum thresholds or growth must be paused — a non-negotiable constraint.",
    ],
}

# ── Detection functions ────────────────────────────────────────────────────────

def detect_industry(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for industry, signals in INDUSTRY_SIGNALS.items():
        score = sum(1 for s in signals if s in text_lower)
        if score > 0:
            scores[industry] = score
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def detect_company_stage(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for stage, signals in COMPANY_STAGE_SIGNALS.items():
        score = sum(1 for s in signals if s in text_lower)
        if score > 0:
            scores[stage] = score
    if not scores:
        return "unknown"
    return max(scores, key=scores.get)


# ── Fact extraction — the only job of ai_engine now ───────────────────────────

def extract_facts(user_input: str) -> dict:
    """
    Extracts lightweight, observable facts from the raw input.
    Does NOT interpret the problem or look up knowledge.
    Knowledge retrieval happens in orchestrator.py via the vector store.
    """
    text = user_input.lower()

    issues = []
    for name, keywords, weight in ISSUE_PATTERNS:
        if any(kw in text for kw in keywords):
            issues.append((name, weight))

    issues = sorted(issues, key=lambda x: x[1], reverse=True)
    main_issue = issues[0][0] if issues else "unclear problem"
    issue_list = [i[0] for i in issues]

    metrics      = _extract_metrics(user_input)
    urgency      = _detect_urgency(text, issue_list, metrics)
    industry     = detect_industry(user_input)
    company_stage = detect_company_stage(user_input)

    return {
        "main_issue":    main_issue,
        "issue_list":    issue_list,
        "urgency":       urgency,
        "metrics":       metrics,
        "raw_input":     user_input,
        "industry":      industry,
        "company_stage": company_stage,
    }


# ── Backward-compat shim for app.py ───────────────────────────────────────────

def structure_problem(user_input: str) -> dict:
    """Alias kept so app.py doesn't break while we migrate."""
    return extract_facts(user_input)


def generate_consulting_response(user_input: str):
    """Routes through orchestrator so the full RAG pipeline is used."""
    from orchestrator import process
    response_text, facts, _chunks = process(user_input)
    return response_text, facts


# ── Urgency detection (v1 — keep exactly) ─────────────────────────────────────

def _detect_urgency(text, issue_list, metrics):
    if any(w in text for w in URGENCY_CRITICAL):
        return "critical"

    pct_values = [float(v.strip("%")) for v in metrics.values() if "%" in v]
    if any(p >= 50 for p in pct_values):
        return "critical"

    if any(w in text for w in URGENCY_HIGH):
        return "high"

    if any(p >= 20 for p in pct_values):
        return "high"

    if any(w in text for w in URGENCY_LOW):
        return "low"

    return "medium" if issue_list else "low"


# ── Metrics extraction (v1 — keep exactly) ────────────────────────────────────

def _extract_metrics(text):
    metrics = {}
    n = 0

    for m in re.findall(r'\d+(?:\.\d+)?\s*%', text):
        metrics[f"pct_{n}"] = m.strip()
        n += 1
        if n >= 3:
            break

    for m in re.findall(r'\$[\d,]+(?:\.\d+)?[kKmMbB]?', text):
        metrics[f"dollar_{len([k for k in metrics if k.startswith('dollar')])}"] = m
        if len(metrics) >= 5:
            break

    match = re.search(r'(\d+)\s*(day|week|month|year)s?', text, re.IGNORECASE)
    if match:
        metrics["timeframe"] = f"{match.group(1)} {match.group(2)}s"

    match = re.search(r'(\d+)x', text)
    if match:
        metrics["multiplier"] = f"{match.group(1)}x"

    return metrics


# ── Input validation ───────────────────────────────────────────────────────────

def validate_consulting_input(text: str) -> tuple:
    """
    Returns (is_valid: bool, rejection_type: str | None, reason: str | None).
    Uses the LLM to judge — falls back to a simple length check only.
    """
    if not text or not text.strip():
        return False, "off_topic", "No input provided."

    if len(text.strip().split()) < 8:
        return (
            False,
            "off_topic",
            "Too brief to structure. Describe what is happening, for how long, "
            "and what you have already tried.",
        )

    # Delegate judgment to the LLM
    from file_processor import _call_classifier
    result = _call_classifier(text[:2000])

    if result is None:
        # LLM unavailable — accept and let the main prompt handle it
        return True, None, None

    if not result.get("accepted", True):
        return False, result.get("type", "off_topic"), result.get("reason", "")

    return True, None, None
