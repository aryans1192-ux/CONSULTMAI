import os
from dotenv import load_dotenv

load_dotenv()

# Set USE_REAL_API=true in .env when you have credits loaded
_USE_MOCK = os.getenv("USE_REAL_API", "false").lower() != "true"

URGENCY_TONE = {
    "critical": "CRITICAL — Immediate action required. ",
    "high":     "HIGH PRIORITY — Address this within the week. ",
    "medium":   "",
    "low":      "Lower urgency — address in next planning cycle. ",
}


def call_claude(analysis: dict) -> str:
    if _USE_MOCK:
        return _mock_response(analysis)

    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    prompt = _build_prompt(analysis)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system="You are an elite management consultant. Be direct, structured, and concrete. Never use filler words.",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def _build_prompt(analysis: dict) -> str:
    metrics_str = ", ".join(analysis["metrics"].values()) if analysis["metrics"] else "none detected"
    return f"""
User problem:
{analysis["raw_input"]}

Pre-analysis:
- Main issue: {analysis["main_issue"]}
- Urgency: {analysis["urgency"]}
- Other issues: {analysis["issue_list"]}
- Detected metrics: {metrics_str}

Return output in EXACTLY this format — no extra text, no paragraphs:

**Situation:**
[1-2 sentence summary of what is actually happening, incorporating any detected metrics]

**Key Components:**
- [issue 1]
- [issue 2]
- [issue 3]

**Priority Flow:**
[Most urgent] -> [Next] -> [Then]

**Execution Steps:**
- Step 1: [action]
- Step 2: [action]
- Step 3: [action]
- Step 4: [action]

**Notes / Risks:**
- [important signal or risk]
- [important signal or risk]
- [important signal or risk]
""".strip()


def _mock_response(analysis: dict) -> str:
    main  = analysis["main_issue"]
    all_  = analysis["issue_list"]
    urg   = analysis["urgency"]
    mets  = analysis["metrics"]

    tone      = URGENCY_TONE.get(urg, "")
    situation = tone + _situation_for(main, mets)

    others = [i for i in all_ if i != main]
    components = [f"- {main.title()}"] + [f"- {o.title()}" for o in others[:3]]
    components_block = "\n".join(components)

    priority = _priority_flow(main, others)
    steps    = _steps_for(main)
    risks    = _risks_for(main)

    return f"""**Situation:**
{situation}

**Key Components:**
{components_block}

**Priority Flow:**
{priority}

**Execution Steps:**
{steps}

**Notes / Risks:**
{risks}""".strip()


# ── Situation ──────────────────────────────────────────────────────────────────

def _situation_for(issue, metrics):
    pct   = next((v for k, v in metrics.items() if k.startswith("pct")),   None)
    money = next((v for k, v in metrics.items() if k.startswith("dollar")), None)
    time_ = metrics.get("timeframe")

    base = {
        "demand decline": (
            f"Business is experiencing a {pct + ' ' if pct else ''}drop in sales or customer demand."
            + (" The decline has been building over " + time_ + "." if time_ else " The decline appears structural and requires urgent diagnosis before it compounds.")
        ),
        "customer dissatisfaction": (
            "Customers are signaling problems through complaints, churn, or negative feedback."
            " Trust is eroding and needs to be addressed before it becomes a reputation issue."
        ),
        "operational inefficiency": (
            "Internal processes are causing delays, rework, or wasted resources."
            " The operation is running but not at the level the business needs."
        ),
        "inefficient marketing": (
            f"Marketing spend{' of ' + money if money else ''} is not converting effectively."
            " CAC is likely rising while returns are shrinking."
        ),
        "financial pressure": (
            "The business is facing cost pressure or profitability decline."
            " Immediate visibility into the P&L is critical to informed decision-making."
        ),
        "cash flow issue": (
            f"The business has{' a ' + time_ + ' ' if time_ else ' a '}cash runway or liquidity mismatch."
            + (f" With {money} involved, the timing of cash in vs. out creates near-term execution risk." if money else " The timing of cash in vs. cash out creates near-term execution risk.")
        ),
        "talent retention": (
            "Key team members are leaving or at risk of leaving."
            " Attrition at this level disrupts execution and signals a deeper cultural or compensation misalignment."
        ),
        "product quality issue": (
            "Product defects or quality issues are generating complaints or incidents."
            " Left unaddressed, this creates compounding trust damage and potential liability."
        ),
        "competitive pressure": (
            "A competitor is actively taking market share through pricing, product, or distribution advantages."
            " Reactive moves without a clear strategy will accelerate the decline."
        ),
        "scaling bottleneck": (
            "Growth is outpacing the business's operational capacity."
            " Infrastructure, team, or process constraints are creating breakdowns at higher volumes."
        ),
        "leadership misalignment": (
            "Leadership lacks a shared direction or has visible strategic disagreement."
            " This creates execution paralysis, conflicting team priorities, and talent risk."
        ),
        "compliance or legal risk": (
            "The business faces regulatory, legal, or compliance exposure."
            " This creates financial risk, operational constraints, and potential reputational damage."
        ),
    }
    return base.get(issue, (
        "A complex, multi-layered problem has been identified."
        " The situation requires structured decomposition before action can be taken effectively."
    ))


# ── Priority Flow ──────────────────────────────────────────────────────────────

def _priority_flow(main, others):
    flows = {
        "demand decline":           "Diagnose root cause -> Stabilize current customers -> Recover lost demand",
        "customer dissatisfaction": "Triage complaints -> Fix top 3 issues -> Rebuild trust",
        "operational inefficiency": "Map current process -> Identify bottlenecks -> Pilot improvements",
        "inefficient marketing":    "Audit channel performance -> Cut waste -> Double down on winners",
        "financial pressure":       "Get full P&L visibility -> Cut non-essentials -> Stabilize margins",
        "cash flow issue":          "Map 13-week cash forecast -> Accelerate receivables -> Delay non-critical payables",
        "talent retention":         "Identify flight risks -> Diagnose root causes -> Implement retention levers",
        "product quality issue":    "Contain active defects -> Diagnose root cause -> Harden QA process",
        "competitive pressure":     "Understand competitor moves -> Identify your defensible moat -> Respond selectively",
        "scaling bottleneck":       "Identify the constraint -> Quantify the cap -> Remove or route around it",
        "leadership misalignment":  "Surface disagreements explicitly -> Align on 3 priorities -> Cascade with clarity",
        "compliance or legal risk": "Assess exposure -> Engage legal counsel -> Build remediation plan",
    }
    flow = flows.get(main, "Clarify the problem -> Break into workstreams -> Execute with ownership")

    if "cash flow issue" in others and main != "cash flow issue":
        flow += " -> Monitor cash position in parallel"
    if "talent retention" in others and main != "talent retention":
        flow += " -> Address team stability"

    return flow


# ── Execution Steps ────────────────────────────────────────────────────────────

def _steps_for(issue):
    steps = {
        "demand decline": (
            "- Step 1: Segment demand data by region, channel, and cohort to isolate where the drop is concentrated\n"
            "- Step 2: Run customer exit interviews or an NPS pulse to surface dissatisfaction signals\n"
            "- Step 3: Review competitor pricing and positioning for any market-level shifts in the last 90 days\n"
            "- Step 4: Launch a targeted retention campaign for your highest-value customer segment"
        ),
        "customer dissatisfaction": (
            "- Step 1: Pull the last 30 days of support tickets and reviews and tag them by theme\n"
            "- Step 2: Identify the top 3 complaint categories and map each to the internal process that caused it\n"
            "- Step 3: Assign a single owner to each category with a 2-week resolution deadline\n"
            "- Step 4: Follow up directly with affected customers to close the loop and rebuild trust"
        ),
        "operational inefficiency": (
            "- Step 1: Map the current workflow end-to-end and record the time spent at each stage\n"
            "- Step 2: Identify the 2-3 stages causing the most delay, rework, or handoff failures\n"
            "- Step 3: Pilot one process improvement on the worst bottleneck — automate, batch, or redesign the handoff\n"
            "- Step 4: Measure cycle time before and after, then roll out to other workflows"
        ),
        "inefficient marketing": (
            "- Step 1: Pull CAC and ROAS by channel for the last 90 days\n"
            "- Step 2: Pause or cut channels where CAC exceeds 3x LTV — reallocate that budget\n"
            "- Step 3: Run 2-3 creative or audience A/B tests on your best-performing channel\n"
            "- Step 4: Set weekly performance reviews to catch degradation early"
        ),
        "financial pressure": (
            "- Step 1: Build a full P&L view — revenue, COGS, gross margin, operating expenses\n"
            "- Step 2: Categorize all costs as fixed vs variable and flag discretionary items\n"
            "- Step 3: Identify the top 3 cost lines to reduce without impacting revenue-generating functions\n"
            "- Step 4: Model base, downside, and upside scenarios for the next two quarters"
        ),
        "cash flow issue": (
            "- Step 1: Build a week-by-week cash in/out forecast for the next 13 weeks\n"
            "- Step 2: Contact your top 5 debtors for accelerated payment or a part-payment arrangement\n"
            "- Step 3: Negotiate a 30-day extension on your top 3 payables — most vendors will agree if you ask\n"
            "- Step 4: Identify any non-core assets or excess inventory that can be liquidated quickly"
        ),
        "talent retention": (
            "- Step 1: Pull 90-day attrition data by role and team — find where the exits are concentrated\n"
            "- Step 2: Run structured stay interviews with your top 10% performers this week\n"
            "- Step 3: Benchmark compensation and benefits against current market rates\n"
            "- Step 4: Build a visible growth and recognition path — people leave when they can't see forward"
        ),
        "product quality issue": (
            "- Step 1: Log and triage all active defects by severity and frequency of occurrence\n"
            "- Step 2: Pause shipping or deployment of the affected product/feature if severity is critical\n"
            "- Step 3: Run a root cause analysis using 5-Why or fishbone — don't patch symptoms\n"
            "- Step 4: Implement a QA gate or regression test before the next release or production run"
        ),
        "competitive pressure": (
            "- Step 1: Map competitor pricing, product changes, and GTM moves in the last 90 days\n"
            "- Step 2: Identify 3 customer segments where you have a structural, defensible advantage\n"
            "- Step 3: Decide your response: match, differentiate, or focus on retention — pick one, commit to it\n"
            "- Step 4: Brief your sales team on the competitive context and give them clear talking points"
        ),
        "scaling bottleneck": (
            "- Step 1: Map the end-to-end system and identify the single biggest throughput constraint\n"
            "- Step 2: Quantify the gap — how much volume can the current system handle vs. what's coming?\n"
            "- Step 3: Prioritize infrastructure, hiring, or process changes to relieve the primary constraint first\n"
            "- Step 4: Build to 2x current demand, not 1.1x — you'll hit the ceiling again within months otherwise"
        ),
        "leadership misalignment": (
            "- Step 1: Schedule a structured alignment session — bring all decision-makers and document disagreements explicitly\n"
            "- Step 2: Narrow to 3 strategic priorities that everyone can commit to for the next 90 days\n"
            "- Step 3: Assign clear ownership and decision rights for each priority — no joint ownership\n"
            "- Step 4: Cascade the agreed direction to all teams within one week before narratives fill the vacuum"
        ),
        "compliance or legal risk": (
            "- Step 1: Document all known compliance gaps with severity, owner, and deadline\n"
            "- Step 2: Engage external legal counsel within 48 hours if any gap carries material financial risk\n"
            "- Step 3: Build a remediation roadmap with hard dates and accountable owners for each item\n"
            "- Step 4: Implement a recurring internal compliance review — monthly is the minimum"
        ),
    }
    return steps.get(issue, (
        "- Step 1: Define the problem with data — avoid acting on assumptions or anecdotes\n"
        "- Step 2: Identify the top 3 stakeholders affected and align everyone on success criteria\n"
        "- Step 3: Break the problem into workstreams, assign clear ownership, and set deadlines\n"
        "- Step 4: Review progress weekly and adjust based on early signals — don't wait for the monthly review"
    ))


# ── Risks ──────────────────────────────────────────────────────────────────────

def _risks_for(issue):
    risks = {
        "demand decline": (
            "- Treating a market-level demand shift as an internal execution problem leads to wrong fixes\n"
            "- Slow response lets competitors absorb your churned customers — speed matters here\n"
            "- Aggressive discounting can erode margin permanently without actually recovering volume"
        ),
        "customer dissatisfaction": (
            "- Unresolved complaints escalate publicly — reviews and social posts move fast\n"
            "- Customers churn before fixes are in place — act in days, not weeks\n"
            "- Internal finger-pointing slows resolution — assign a single owner per issue, not a committee"
        ),
        "operational inefficiency": (
            "- Teams revert to old habits after initial improvements — the change needs to be measured to stick\n"
            "- Scope creep turns a focused fix into a long restructuring project that never ships\n"
            "- Without before/after metrics, you won't know if the improvement actually worked"
        ),
        "inefficient marketing": (
            "- Poor attribution setup means you may be penalizing the wrong channels — audit tracking first\n"
            "- Cutting spend too aggressively creates a demand vacuum that hurts pipeline 60-90 days later\n"
            "- Creative fatigue silently inflates CAC over time — refresh assets on a regular cadence"
        ),
        "financial pressure": (
            "- Cutting costs without understanding which costs drive revenue will shrink the business, not fix it\n"
            "- Financial stress leaks into team morale if leadership doesn't communicate with honesty\n"
            "- Margin and cash flow are different problems — make sure you're solving the right one"
        ),
        "cash flow issue": (
            "- Waiting until the account is nearly empty eliminates all negotiating leverage with vendors and investors\n"
            "- Vendors notice slow payment — proactive communication preserves the relationship\n"
            "- Cash flow and profitability are different problems — you can be profitable and still run out of cash"
        ),
        "talent retention": (
            "- Exit interviews are almost always too late — use stay interviews proactively, not reactively\n"
            "- Counteroffers work short-term but rarely fix the root cause — the person will likely leave within 6 months anyway\n"
            "- When peers leave, remaining team morale drops — communicate quickly and honestly"
        ),
        "product quality issue": (
            "- Shipping known defects erodes trust with your team — it signals that quality isn't actually a priority\n"
            "- Public defect disclosures require a prepared communications response — don't get caught flat-footed\n"
            "- QA shortcuts to hit deadlines create compounding technical debt that slows all future development"
        ),
        "competitive pressure": (
            "- Matching every competitor move is a race to the bottom — be selective and strategic\n"
            "- Price wars destroy margin for everyone — only engage if you have the runway to outlast\n"
            "- Customer perception of your brand matters more than feature parity — own your differentiation"
        ),
        "scaling bottleneck": (
            "- Adding headcount without fixing the underlying process just scales the inefficiency\n"
            "- Infrastructure investments always take longer than estimated — start the procurement cycle now\n"
            "- Over-building for scale before you have consistent demand is equally dangerous — size it carefully"
        ),
        "leadership misalignment": (
            "- Misalignment at the top is immediately visible to the team even when it isn't discussed openly\n"
            "- Delayed resolution leads to shadow decision-making and political silos that are hard to undo\n"
            "- Consensus-seeking without a designated decision-maker leads to permanent stalemate"
        ),
        "compliance or legal risk": (
            "- Assuming internal counsel is sufficient for material regulatory risk is a common and costly mistake\n"
            "- Fines and penalties compound if violations continue after you become aware of them\n"
            "- Proactive disclosure to regulators is almost always better than reactive discovery — consult counsel on timing"
        ),
    }
    return risks.get(issue, (
        "- Without assigned ownership, even the best plans stall indefinitely\n"
        "- Over-analysis delays execution — set a decision deadline and stick to it\n"
        "- Misaligned stakeholders will pull the team in conflicting directions — get alignment before acting"
    ))
