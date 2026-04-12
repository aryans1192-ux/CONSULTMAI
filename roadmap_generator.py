"""
roadmap_generator.py
Parses the ConsultMAI LLM / mock output text into the structured roadmap dict
that chart_component.render_execution_chart() consumes.

The LLM and mock both produce:
  [PHASE N — LABEL (timeframe): what you are doing]
  - Step N: action text | Owner: role | Due: timeline | Output: deliverable

We parse that directly so the chart carries exactly the same rich content as
the text output — no generic templates.
"""

import re


# ── Public API ─────────────────────────────────────────────────────────────────

def build_roadmap_from_text(response_text: str, analysis: dict) -> dict:
    """
    Parse the LLM/mock response into a roadmap dict.
    Falls back to a minimal scaffold only if parsing yields nothing.
    """
    phases = _parse_phases(response_text, analysis)
    if not phases:
        phases = _fallback_phases(analysis)

    return {
        "title": _make_title(analysis),
        "phases": phases,
    }


# ── Phase parser ───────────────────────────────────────────────────────────────

# Matches:  [PHASE 1 — IMMEDIATE (0–48 hrs): stopping the revenue bleed]
# Also:     [PHASE 2 — DIAGNOSIS (Days 3–7): confirming root cause]
_PHASE_HDR = re.compile(
    r'\[PHASE\s+\d+\s*[—–-]\s*'         # [PHASE N —
    r'([A-Z][^()\[\]]*?)'               # LABEL
    r'(?:\(([^)]+)\))?'                  # (timeframe)  optional
    r'(?:\s*:\s*([^\]]+))?'             # : description  optional
    r'\]',
    re.IGNORECASE,
)

# Matches: - Step N: action | Owner: role | Due: timeline | Output: deliverable
# Also handles mock long-form: - Step N: full prose sentence (no pipes)
_STEP_LINE = re.compile(
    r'^-\s+Step\s+\d+\s*:\s*(.+)',
    re.IGNORECASE,
)


def _parse_phases(text: str, analysis: dict) -> list:
    """Extract phases from the Execution Steps section of the LLM output."""
    # Pull just the Execution Steps block (ignore Situation / Key Components)
    exec_match = re.search(
        r'\*\*Execution Steps:\*\*\s*(.*)',
        text,
        re.DOTALL | re.IGNORECASE,
    )
    body = exec_match.group(1) if exec_match else text

    # Also strip anything after Notes/Risks
    notes_match = re.search(r'\*\*Notes', body, re.IGNORECASE)
    if notes_match:
        body = body[:notes_match.start()]

    urgency   = analysis.get("urgency", "medium")
    lines     = body.splitlines()
    phases    = []
    cur_phase = None

    for line in lines:
        line = line.rstrip()
        ph   = _PHASE_HDR.search(line)

        if ph:
            if cur_phase and cur_phase["nodes"]:
                phases.append(cur_phase)

            label     = ph.group(1).strip().title()
            timeframe = (ph.group(2) or "").strip()
            # desc      = (ph.group(3) or "").strip()  # available if needed

            # Urgency: inherit from analysis for phase 1, guess from label for others
            ph_urgency = urgency if not phases else _guess_urgency_from_label(label)

            cur_phase = {
                "title":     label,
                "timeframe": timeframe,
                "urgency":   ph_urgency,
                "nodes":     [],
            }
            continue

        if cur_phase is None:
            continue

        st = _STEP_LINE.match(line)
        if not st:
            continue

        content = st.group(1).strip()
        node    = _parse_step_content(content)
        if node:
            cur_phase["nodes"].append(node)

    if cur_phase and cur_phase["nodes"]:
        phases.append(cur_phase)

    return phases


def _parse_step_content(content: str) -> dict | None:
    """
    Parse a step line into a node dict.

    Two formats supported:
    A) "action sentence | Owner: role | Due: timeline | Output: deliverable"
    B) "full prose — no pipes"
    """
    parts = [p.strip() for p in content.split("|")]

    if len(parts) >= 4:
        # Format A — pipe-separated
        action_raw  = parts[0]
        owner_raw   = parts[1]
        due_raw     = parts[2]
        output_raw  = parts[3]

        owner  = re.sub(r'^Owner\s*:\s*', '', owner_raw,  flags=re.IGNORECASE).strip()
        due    = re.sub(r'^Due\s*:\s*',   '', due_raw,    flags=re.IGNORECASE).strip()
        output = re.sub(r'^Output\s*:\s*','', output_raw, flags=re.IGNORECASE).strip()

        # Action text: everything up to the first " — " or " ; " or end
        action_text = re.split(r'\s*—\s*|\s*;\s*', action_raw, maxsplit=1)[0].strip()
        # Full description is the complete action_raw sentence
        description = action_raw.strip()

        title = _shorten_title(action_text)

    else:
        # Format B — prose only (mock long-form)
        # "Pull all attrition data for the last 6 months — HR lead owns this
        #  within 24 hours; output is a ranked breakdown showing..."
        action_raw  = content

        # Split on " — " to get title vs. detail
        dash_split = re.split(r'\s+—\s+', action_raw, maxsplit=1)
        title       = _shorten_title(dash_split[0])
        description = action_raw

        # Try to extract owner from "— <Role> owns this"
        owner_m = re.search(r'—\s*(.+?)\s+owns this', action_raw, re.IGNORECASE)
        owner   = owner_m.group(1).strip() if owner_m else ""

        # Try to extract output from "; output is ..."
        output_m = re.search(r';\s*output is\s+(.+)', action_raw, re.IGNORECASE)
        output   = _shorten_title(output_m.group(1)) if output_m else ""

        due = ""

    if not title:
        return None

    return {
        "title":       title,
        "description": description,
        "owner":       owner,
        "output":      output,
        "due":         due,
    }


def _shorten_title(text: str, max_len: int = 55) -> str:
    """Trim a sentence to a readable node title."""
    text = text.strip().rstrip(".")
    # Drop leading boilerplate like "Pull ", "Build ", "Identify ", etc. if > max_len
    if len(text) <= max_len:
        return text
    # Cut at last word boundary before max_len
    cut = text[:max_len]
    last_space = cut.rfind(" ")
    if last_space > max_len // 2:
        cut = cut[:last_space]
    return cut + "…"


def _guess_urgency_from_label(label: str) -> str:
    label = label.lower()
    if any(w in label for w in ("immediate", "critical", "emergency", "stop")):
        return "critical"
    if any(w in label for w in ("diagnosis", "diagnos", "assess", "triage")):
        return "high"
    if any(w in label for w in ("stabilise", "stabiliz", "fix", "repair")):
        return "medium"
    return "low"


# ── Title builder ──────────────────────────────────────────────────────────────

def _make_title(analysis: dict) -> str:
    _labels = {
        "demand decline":           "Revenue Recovery Plan",
        "cash flow issue":          "Cash Flow Rescue Plan",
        "operational inefficiency": "Operations Improvement Plan",
        "talent retention":         "Talent Retention Programme",
        "competitive pressure":     "Competitive Defence Plan",
        "customer dissatisfaction": "Customer Experience Fix",
        "inefficient marketing":    "Marketing Performance Overhaul",
        "financial pressure":       "Financial Stabilisation Plan",
        "product quality issue":    "Quality Recovery Programme",
        "scaling bottleneck":       "Scale-Up Execution Plan",
        "leadership misalignment":  "Leadership Alignment Sprint",
        "compliance or legal risk": "Risk Remediation Roadmap",
    }
    issue    = analysis.get("main_issue", "")
    industry = analysis.get("industry", "general")
    label    = _labels.get(issue, "Execution Roadmap")
    if industry and industry not in ("general", ""):
        return f"{label} — {industry.upper()}"
    return label


# ── Fallback (used only when text parse yields nothing) ────────────────────────

def _fallback_phases(analysis: dict) -> list:
    urgency = analysis.get("urgency", "medium")
    return [
        {
            "title":     "Diagnose",
            "timeframe": "Week 1",
            "urgency":   urgency,
            "nodes": [
                {"title": "Decompose the problem with MECE logic",    "description": "Break the problem into its non-overlapping components. Identify which sub-problem has the largest revenue or cost impact.", "owner": "CEO / Strategy Lead", "output": "Problem tree", "due": "Day 2"},
                {"title": "Quantify the gap — baseline vs. target",   "description": "Establish the current-state metric and the target. The delta IS the problem. Everything else is hypothesis.", "owner": "Analytics Lead",      "output": "Gap analysis",    "due": "Day 3"},
                {"title": "Confirm root cause vs. symptom (5-Why)",   "description": "Apply 5-Why to the top hypothesis. The first answer is almost always a symptom. Iterate until you reach a controllable cause.", "owner": "Cross-functional",  "output": "Root cause doc",  "due": "Day 5"},
            ],
        },
        {
            "title":     "Design the Fix",
            "timeframe": "Week 2",
            "urgency":   "medium",
            "nodes": [
                {"title": "Generate 3 solution options with trade-offs", "description": "Produce distinct solution paths with different risk/speed/cost profiles. Avoid anchoring on the first idea.", "owner": "Strategy Lead",   "output": "Options brief",       "due": "Day 8"},
                {"title": "Select and commit to one path",               "description": "Score options against impact, reversibility, and resource cost. Pick one and issue a clear decision memo.", "owner": "CEO",             "output": "Decision memo",       "due": "Day 10"},
                {"title": "Break into weekly milestones with owners",    "description": "Translate the solution into a week-by-week plan. Every milestone has a named owner and a measurable output.", "owner": "Project Lead",    "output": "Implementation plan", "due": "Day 12"},
            ],
        },
        {
            "title":     "Execute",
            "timeframe": "Weeks 3–8",
            "urgency":   "low",
            "nodes": [
                {"title": "Launch with weekly 30-min checkpoint calls",  "description": "Flag blockers immediately — do not let them sit until the next meeting. Update the plan in real time.", "owner": "CEO / Project Lead", "output": "Weekly status",    "due": "Weekly"},
                {"title": "Measure impact vs. baseline every week",      "description": "Track the core metric weekly. If no movement by week 4, escalate and revisit the root cause hypothesis.", "owner": "Analytics Lead",    "output": "Impact dashboard", "due": "Weekly"},
            ],
        },
    ]
