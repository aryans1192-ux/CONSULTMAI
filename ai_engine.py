import re

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


def structure_problem(user_input):
    text = user_input.lower()

    issues = []
    for name, keywords, weight in ISSUE_PATTERNS:
        if any(kw in text for kw in keywords):
            issues.append((name, weight))

    issues = sorted(issues, key=lambda x: x[1], reverse=True)
    main_issue = issues[0][0] if issues else "unclear problem"
    issue_list = [i[0] for i in issues]

    metrics = _extract_metrics(user_input)
    urgency = _detect_urgency(text, issue_list, metrics)

    return {
        "main_issue": main_issue,
        "issue_list": issue_list,
        "urgency": urgency,
        "metrics": metrics,
        "raw_input": user_input,
    }


def generate_consulting_response(user_input):
    from llm_client import call_claude

    analysis = structure_problem(user_input)
    response_text = call_claude(analysis)
    return response_text, analysis


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
