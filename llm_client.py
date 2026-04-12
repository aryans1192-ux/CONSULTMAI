"""
ConsultMAI LLM client — provider chain with intelligent mock fallback.
Priority: Groq (free) → Gemini (free) → Anthropic → Smart Mock
"""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USE_REAL_API      = os.getenv("USE_REAL_API", "false").lower() == "true"

SYSTEM_PROMPT = (
    "You are a senior partner at McKinsey & Company specialising in turnarounds and operational transformations. "
    "Your standard: if a recommendation could appear in a response to a DIFFERENT company's problem, it is too generic and must be rewritten. "
    "Every sentence must earn its place by containing at least one of: a specific number, a named role, a named framework applied to THIS situation, a concrete action with a deadline, or a measurable output. "
    "Banned phrases: 'improve', 'optimise', 'address', 'consider', 'focus on', 'it is important to', 'leverage', 'streamline', 'enhance'. "
    "When the user gives you numbers — quote them back. When they give you an industry — use that industry's specific benchmarks and failure modes. "
    "The test for every sentence: could a different CEO read this and think it was written for them? If yes, rewrite it until only THIS CEO could recognise it."
)


# ── Public entry point ─────────────────────────────────────────────────────────

def call_llm(facts: dict, retrieved_chunks: list[dict] | None = None) -> str:
    """
    Try providers in order: Groq → Gemini → Anthropic → Smart Mock.
    retrieved_chunks: list of {"text": str, "metadata": dict, "distance": float}
    from the vector store. When present, the prompt is built from real retrieved
    context instead of hardcoded playbooks.
    """
    chunks = retrieved_chunks or []

    if not USE_REAL_API:
        return _smart_mock(facts, chunks)

    if GROQ_API_KEY:
        try:
            return _call_groq(facts, chunks)
        except Exception:
            pass

    if GEMINI_API_KEY:
        try:
            return _call_gemini(facts, chunks)
        except Exception:
            pass

    if ANTHROPIC_API_KEY:
        try:
            return _call_anthropic(facts, chunks)
        except Exception:
            pass

    return _smart_mock(facts, chunks)


# Backward-compat alias
call_claude = call_llm


# ── Providers ──────────────────────────────────────────────────────────────────

def _call_groq(facts: dict, chunks: list[dict]) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    prompt = _build_prompt(facts, chunks)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=3000,
        temperature=0.25,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    return response.choices[0].message.content


def _call_gemini(facts: dict, chunks: list[dict]) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    prompt = _build_prompt(facts, chunks)
    response = model.generate_content(
        prompt,
        generation_config={"max_output_tokens": 3000, "temperature": 0.25},
    )
    return response.text


def _call_anthropic(facts: dict, chunks: list[dict]) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = _build_prompt(facts, chunks)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ── Prompt builder — context comes from retrieval, not hardcoding ──────────────

def _build_prompt(facts: dict, chunks: list[dict]) -> str:
    metrics_str = ", ".join(facts.get("metrics", {}).values()) or "none detected"

    # Build retrieved context block — this is what makes it non-generic
    if chunks:
        context_block = "\n\n".join(
            f"[Source: {c['metadata'].get('source', 'unknown')}]\n{c['text']}"
            for c in chunks
        )
    else:
        context_block = "No knowledge retrieved — reason from first principles."

    # Legacy compat: if old-style analysis dict passed (root_causes/benchmarks keys present)
    root_causes_str = "\n".join(f"  - {q}" for q in facts.get("root_causes", []))
    benchmarks_str  = "\n".join(f"  - {b}" for b in facts.get("benchmarks", []))

    industry = facts.get("industry", "general")

    return f"""
You are analysing a real business problem. Use the pre-analysis and retrieved knowledge below.
Produce output in EXACTLY the format shown — no extra text, no preamble.

=== FACTS EXTRACTED FROM INPUT ===
Raw input: {facts.get("raw_input", "")}
Main issue signal: {facts.get("main_issue", "unclear")}
All issue signals: {", ".join(facts.get("issue_list", []))}
Urgency: {facts.get("urgency", "medium")}
Industry: {industry}
Company stage: {facts.get("company_stage", "unknown")}
Detected metrics: {metrics_str}

=== RETRIEVED KNOWLEDGE (use this — do not invent benchmarks or playbooks) ===
{context_block}

=== REQUIRED OUTPUT FORMAT ===

**Situation:**
[2–3 sentences. You MUST quote the user's exact numbers, timeframes, and words back at them. Name the specific failure mechanism — not "revenue is declining" but "the business is losing volume in [specific channel/segment from the input] because [specific cause], and at the current rate that means [consequence using their numbers]". If no numbers exist, name the stage and what that stage typically breaks at. Use the retrieved knowledge above to make this specific to their industry and context.]

**Key Components:**
[4 components. Each component is a specific mechanism breaking down, not a label. Format: "Name — what it is doing to the business right now and what it will do if not fixed in 30 days". Example of BAD: "Revenue Decline". Example of GOOD: "CAC payback extending past 18 months — means each new customer costs more to acquire than they return before churn, making growth structurally loss-making at scale". Use numbers from the input. Make the causal chain explicit.]
- [Component 1]
- [Component 2]
- [Component 3]
- [Component 4]

**Priority Flow:**
[A sequence of 4–5 steps where each step is a specific verb-led action and the arrow means "which unlocks". Format: "Action (metric or output it produces)" -> "Action (why this must come second)" -> "Action" -> "Action". Example of BAD: "Diagnose -> Fix -> Scale". Example of GOOD: "Segment revenue by cohort (produces the loss attribution table) -> Kill the loss-making cohort spend (stops the cash drain) -> Reallocate budget to the 2 winning channels (CAC drops below target) -> Rebuild retention flywheel (LTV recovers)". Every step must be specific to THIS company's situation.]

**Execution Steps:**

[PHASE 1 — IMMEDIATE (0–48 hrs): {{what you are stopping right now}}]
- Step 1: {{action}} | Owner: {{role}} | Due: {{24h or 48h}} | Output: {{exact deliverable}}
- Step 2: {{action}} | Owner: {{role}} | Due: {{timeline}} | Output: {{deliverable}}
- Step 3: {{action}} | Owner: {{role}} | Due: {{timeline}} | Output: {{deliverable}}

[PHASE 2 — DIAGNOSIS (Days 3–7): {{root cause you are confirming}}]
- Step 4: {{action}} | Owner: {{role}} | Due: {{Day X}} | Output: {{deliverable}}
- Step 5: {{action}} | Owner: {{role}} | Due: {{Day X}} | Output: {{deliverable}}
- Step 6: {{action}} | Owner: {{role}} | Due: {{Day 7}} | Output: {{single confirmed root cause statement}}

[PHASE 3 — STABILISATION (Weeks 2–4): {{structural driver you are fixing}}]
- Step 7: {{action}} | Owner: {{role}} | Due: {{Week 2}} | Output: {{deliverable}}
- Step 8: {{action}} | Owner: {{role}} | Due: {{Week 3}} | Output: {{deliverable}}
- Step 9: {{action}} | Owner: {{role}} | Due: {{Week 4}} | Output: {{deliverable}}

[PHASE 4 — RECOVERY (Month 2–3): {{what you are building so this cannot recur}}]
- Step 10: {{action}} | Owner: {{role}} | Due: {{Month 2}} | Output: {{deliverable}}
- Step 11: {{action}} | Owner: {{role}} | Due: {{Month 2}} | Output: {{deliverable}}
- Step 12: {{action}} | Owner: {{role}} | Due: {{Month 3}} | Output: {{board-ready artefact confirming structural recovery}}

**Notes / Risks:**
- [Risk 1 — specific, not generic]
- [Risk 2]
- [Risk 3]
""".strip()


# ── Smart mock — uses retrieved chunks, falls back gracefully ──────────────────

def _smart_mock(facts: dict, chunks: list[dict]) -> str:
    """
    Mock output for when no LLM API is available.
    Uses retrieved knowledge chunks to stay non-generic.
    The more docs in the knowledge store, the better this gets.
    """
    main          = facts.get("main_issue", "unclear problem")
    urgency       = facts.get("urgency", "medium")
    metrics       = facts.get("metrics", {})
    industry      = facts.get("industry", "general")
    company_stage = facts.get("company_stage", "unknown")
    raw_input     = facts.get("raw_input", "")

    urgency_prefix = {
        "critical": "CRITICAL — Immediate action required. ",
        "high":     "HIGH PRIORITY — Address within the week. ",
        "medium":   "",
        "low":      "Lower urgency — address in the next planning cycle. ",
    }.get(urgency, "")

    pct   = next((v for k, v in metrics.items() if k.startswith("pct")),    None)
    money = next((v for k, v in metrics.items() if k.startswith("dollar")), None)
    time_ = metrics.get("timeframe")

    metric_str = ""
    if pct:   metric_str += f" of {pct}"
    if money: metric_str += f" ({money} at stake)"
    if time_: metric_str += f" over {time_}"

    industry_tag   = f" ({industry.upper()} context)" if industry not in ("general", "") else ""
    stage_tag      = f" [{company_stage} stage]"     if company_stage not in ("unknown", "") else ""

    situation = (
        f"{urgency_prefix}The business{industry_tag}{stage_tag} presents a {main} signal{metric_str}. "
        f"The retrieved knowledge below contains the relevant frameworks and benchmarks for this context. "
        f"A full LLM analysis is available once an API key is configured."
    )

    # Pull priority flow and relevant steps from retrieved chunks if available
    flow_line = "Diagnose root cause → Stop the bleeding → Fix the driver → Build resilience"
    steps_preview = ""
    for chunk in chunks:
        text = chunk.get("text", "")
        if "Priority Flow" in text:
            for line in text.splitlines():
                if "→" in line or "->" in line:
                    flow_line = line.strip("# ").strip()
                    break
        if "PHASE 1" in text and not steps_preview:
            steps_preview = text[:600]

    components_block = "\n".join(
        f"- {c['text'][:120]}..." if len(c['text']) > 120 else f"- {c['text']}"
        for c in chunks[:3]
    ) or "- Enable the knowledge store by running: python -m ingestion.ingest"

    steps_block = steps_preview or (
        "[PHASE 1 — IMMEDIATE (0–48 hrs)]\n"
        "- Enable real LLM analysis by setting USE_REAL_API=true and providing an API key.\n"
        "- Run python -m ingestion.ingest to populate the knowledge store.\n\n"
        "[Mock mode active — output above is structure-only, not case-specific analysis.]"
    )

    risks_block = (
        "- Mock mode active: this output shows structure, not case-specific analysis.\n"
        "- Set USE_REAL_API=true in .env and add a GROQ_API_KEY (free) for real output.\n"
        "- Run python -m ingestion.ingest once to embed the knowledge base."
    )

    return (
        f"**Situation:**\n{situation}\n\n"
        f"**Key Components (retrieved context):**\n{components_block}\n\n"
        f"**Priority Flow:**\n{flow_line}\n\n"
        f"**Execution Steps:**\n{steps_block}\n\n"
        f"**Notes / Risks:**\n{risks_block}"
    ).strip()


# ── OLD hardcoded builders — kept below as dead code during migration ──────────
# These are no longer called. The LLM now uses retrieved context from the
# knowledge store instead of these templates. Safe to delete once fully migrated.

# ── Situation builder ──────────────────────────────────────────────────────────

def _build_situation(main, metrics, urgency, industry, company_stage):
    pct   = next((v for k, v in metrics.items() if k.startswith("pct")),   None)
    money = next((v for k, v in metrics.items() if k.startswith("dollar")), None)
    time_ = metrics.get("timeframe")

    urgency_prefix = {
        "critical": "CRITICAL — Immediate action required. ",
        "high":     "HIGH PRIORITY — Address within the week. ",
        "medium":   "",
        "low":      "Lower urgency — address in the next planning cycle. ",
    }.get(urgency, "")

    industry_tag = f" ({industry.upper()} context)" if industry not in ("general", "") else ""
    stage_tag    = f" [{company_stage} stage]" if company_stage not in ("unknown", "") else ""

    base = {
        "demand decline": (
            f"The business{industry_tag}{stage_tag} is experiencing a {pct + ' ' if pct else ''}decline in sales or customer demand."
            + (f" The drop has been building over {time_}." if time_ else " The pattern appears structural and requires immediate segmentation before action.")
        ),
        "customer dissatisfaction": (
            f"Customer trust is eroding{industry_tag}{stage_tag} through complaints, churn signals, or public negative feedback."
            " Without containment this week, reputational damage compounds and is far harder to reverse."
        ),
        "operational inefficiency": (
            f"Internal processes{industry_tag}{stage_tag} are creating delays, rework, or resource waste that the business can no longer absorb."
            " The operation is running but at a level that is holding back growth and increasing cost per unit delivered."
        ),
        "inefficient marketing": (
            f"Marketing investment{' of ' + money if money else ''}{industry_tag}{stage_tag} is not converting at an acceptable rate."
            " CAC is likely rising while returns diminish — a pattern that will drain cash without a structured channel audit."
        ),
        "financial pressure": (
            f"The business{industry_tag}{stage_tag} is facing margin compression or profitability deterioration."
            + (f" With {money} at stake, " if money else " ")
            + "full P&L visibility is the prerequisite for any credible corrective action."
        ),
        "cash flow issue": (
            f"The business{industry_tag}{stage_tag} has a cash timing or liquidity problem"
            + (f" with {money} involved" if money else "")
            + (f" and approximately {time_} of visibility" if time_ else "")
            + ". The gap between cash in and cash out creates near-term operational risk that must be forecasted and managed this week."
        ),
        "talent retention": (
            f"Key talent is leaving or at active flight risk{industry_tag}{stage_tag}."
            " Attrition at this level signals a deeper cultural, compensation, or management failure — and disrupts execution faster than most leaders anticipate."
        ),
        "product quality issue": (
            f"Product defects or quality failures{industry_tag}{stage_tag} are generating customer incidents and internal escalations."
            " Left unresolved, this creates compounding trust damage, liability exposure, and development velocity loss."
        ),
        "competitive pressure": (
            f"A competitor is actively gaining ground{industry_tag}{stage_tag} — through pricing, product, or distribution moves that are changing buyer decisions."
            " Reacting without a clear strategic framing will accelerate market share loss."
        ),
        "scaling bottleneck": (
            f"Growth is outpacing the business's current operational capacity{industry_tag}{stage_tag}."
            " Infrastructure, team, or process constraints are creating visible breakdowns at current volume — and the situation worsens as demand increases."
        ),
        "leadership misalignment": (
            f"The leadership team{industry_tag}{stage_tag} lacks a shared direction or has visible strategic disagreement."
            " This creates execution paralysis, conflicting team priorities, and an environment where top talent starts looking for the exit."
        ),
        "compliance or legal risk": (
            f"The business{industry_tag}{stage_tag} faces regulatory, legal, or compliance exposure"
            + (f" with potential {money} in financial risk" if money else "")
            + ". This creates financial liability, operational constraints, and reputational risk that must be assessed and contained immediately."
        ),
    }.get(main, (
        f"A complex multi-issue situation{industry_tag}{stage_tag} requires structured decomposition before any corrective action is taken."
        " Acting without clarity on the primary driver will produce conflicting workstreams and wasted effort."
    ))

    return urgency_prefix + base


# ── Components builder ─────────────────────────────────────────────────────────

def _build_components(main, issue_list):
    others = [i for i in issue_list if i != main]
    lines  = [f"- {main.title()} (primary)"] + [f"- {o.title()}" for o in others[:3]]
    return "\n".join(lines)


# ── Priority flow builder ──────────────────────────────────────────────────────

def _build_priority_flow(main, issue_list):
    flows = {
        "demand decline":           "Segment the demand drop -> Confirm root cause -> Stabilise existing customers -> Recover lost volume",
        "customer dissatisfaction": "Contain active complaints -> Map failure points -> Fix and close loop -> Prevent recurrence",
        "operational inefficiency": "Measure current state -> Find binding constraint -> Pilot fix -> Embed and scale",
        "inefficient marketing":    "Audit channel performance -> Stop waste spend -> Rebuild winning channels -> Install governance",
        "financial pressure":       "Get full P&L visibility -> Categorise and cut costs -> Stabilise gross margin -> Scenario plan",
        "cash flow issue":          "Build 13-week cash forecast -> Accelerate receivables -> Slow non-critical payables -> Structural liquidity fix",
        "talent retention":         "Identify flight risks -> Diagnose root causes -> Deploy immediate retention levers -> Structural rebuild",
        "product quality issue":    "Contain and stop shipping defects -> Root cause analysis -> Fix the process -> Harden QA",
        "competitive pressure":     "Map the competitive attack -> Find defensible edge -> Choose and commit to response -> Arm the team",
        "scaling bottleneck":       "Identify binding constraint -> Quantify the gap -> Remove the constraint -> Build to 2x capacity",
        "leadership misalignment":  "Surface disagreements explicitly -> Force priority alignment -> Assign decision rights -> Cascade and govern",
        "compliance or legal risk": "Assess and document exposure -> Engage counsel -> Build remediation roadmap -> Embed compliance governance",
    }
    flow = flows.get(main, "Clarify the problem -> Break into workstreams -> Assign ownership -> Execute and measure")

    others = [i for i in issue_list if i != main]
    if "cash flow issue" in others and main != "cash flow issue":
        flow += " -> Monitor cash position in parallel"
    if "talent retention" in others and main != "talent retention":
        flow += " -> Address team stability"

    return flow


# ── Execution steps builder ────────────────────────────────────────────────────

def _build_steps(main: str) -> str:

    steps_map = {

        # ── 1. DEMAND DECLINE ──────────────────────────────────────────────────
        "demand decline": """
[PHASE 1 — IMMEDIATE (0–48 hrs): stopping the revenue bleed]
- Step 1: Pull sales data segmented by region, channel, product line, and customer cohort for the last 90 days — the CEO and head of Sales own this within 24 hours; output is a ranked breakdown showing exactly where the volume drop is concentrated.
- Step 2: Freeze any pending pricing increases or product discontinuations until the root cause is confirmed — the COO owns this freeze decision within 24 hours; output is a written hold directive circulated to Sales and Ops.
- Step 3: Contact your top 20 accounts personally (CEO or senior Sales lead) with a structured check-in to surface dissatisfaction signals and buy goodwill — output is a written summary of customer sentiment from those conversations, completed within 48 hours.

[PHASE 2 — DIAGNOSIS (Days 3–7): confirming whether this is market-wide or self-inflicted]
- Step 4: Run 10 structured exit interviews with churned or lapsed customers in the last 60 days — Analytics or CX lead owns this; output is a coded transcript identifying the top 3 reasons for departure.
- Step 5: Map every internal change made in the last 90 days (pricing, product, team, territory coverage, marketing spend) against the timeline of the demand drop — Head of Strategy owns this analysis; output is a correlation map with the 2–3 highest-likelihood internal drivers.
- Step 6: Brief the board or investors with a confirmed root cause statement — CEO owns this by Day 7; output is a one-page memo stating: the primary cause, what has been ruled out, and the corrective plan.

[PHASE 3 — STABILISATION (Weeks 2–4): fixing the primary demand driver]
- Step 7: Launch a targeted retention and win-back campaign for your highest-value customer segment using the exit interview findings to address the specific objection — CMO owns this; output is a live campaign with segment-specific messaging by end of Week 2.
- Step 8: Restructure sales coverage or territory assignments if the drop is concentrated in specific reps or regions — Sales Director owns this by Week 3; output is a revised coverage model and a performance improvement plan for underperforming reps.
- Step 9: Conduct a pricing and value proposition audit against the top 3 competitors — Strategy or Product lead owns this; output is a recommendation memo on whether to adjust price, reframe the offer, or invest in a specific feature to close the competitive gap.

[PHASE 4 — RECOVERY (Month 2–3): structural resilience so this cannot recur]
- Step 10: Implement a monthly demand health dashboard tracking pipeline, win rate, churn rate, and revenue by segment — Analytics owns this build; output is a live dashboard with automated weekly alerts reviewed by the CEO every Monday.
- Step 11: Launch a structured Voice of Customer programme (quarterly NPS + bi-annual in-depth interviews) to provide early warning before demand deterioration becomes visible in revenue — CX lead owns this; output is the first full NPS report with segment-level scores.
- Step 12: Present a board-ready Demand Recovery Report at the Month 3 business review — CEO presents; output is a documented narrative showing the root cause identified, interventions made, volume recovered, and the early-warning system now in place to prevent recurrence.
""".strip(),

        # ── 2. CUSTOMER DISSATISFACTION ───────────────────────────────────────
        "customer dissatisfaction": """
[PHASE 1 — IMMEDIATE (0–48 hrs): containing public damage]
- Step 1: Pull every support ticket, review, and complaint from the last 30 days and tag each one by theme — CX lead owns this within 24 hours; output is a tagged spreadsheet with frequency counts by complaint category.
- Step 2: Identify the top 3 complaint categories and for each one, assign a single named owner with a resolution mandate — CEO or COO assigns these owners within 24 hours; output is a written ownership brief with the problem statement, impacted customer count, and resolution deadline.
- Step 3: Personally contact the 10 most severely affected customers with a direct acknowledgement, no script — CEO or senior account lead completes these calls within 48 hours; output is a call log with individual commitments made and follow-up actions.

[PHASE 2 — DIAGNOSIS (Days 3–7): mapping every failure point in the customer journey]
- Step 4: Map the end-to-end customer journey and mark every touchpoint where a complaint has originated in the last 90 days — CX and Operations leads co-own this; output is an annotated journey map with failure rates at each stage.
- Step 5: Trace each top complaint category back to its internal process root cause using 5-Why analysis — each complaint owner runs their own analysis; output is three root cause statements, one per category, written without euphemism.
- Step 6: Validate the root cause findings with a 10-person customer feedback panel (phone or survey) — CX lead owns this; output by Day 7 is confirmed customer language describing the failure, usable verbatim in internal communications and fix briefs.

[PHASE 3 — STABILISATION (Weeks 2–4): fixing root causes and closing the loop]
- Step 7: Implement the highest-priority fix for the top complaint category and communicate the change directly to affected customers — the assigned owner delivers this by Week 2; output is a deployed fix and a personalised outreach message sent to all customers who raised that complaint.
- Step 8: Retrain or re-brief frontline staff on the revised process and empower them with clear escalation authority so they can resolve issues without management approval — HR and Operations own this; output is a completed training session and an updated escalation policy document.
- Step 9: Re-contact all customers who were promised follow-up during Phase 1 to confirm resolution — CX lead owns this; output is a 100% follow-up rate confirmed, with a closed-loop log showing each customer's status.

[PHASE 4 — RECOVERY (Month 2–3): building systems so this cannot recur]
- Step 10: Launch a monthly CX health report tracking NPS, complaint volume by category, resolution time, and re-contact rate — Analytics builds this; output is a live dashboard reviewed by the COO weekly.
- Step 11: Implement a proactive customer check-in programme targeting customers who have not engaged in 60+ days — CX lead owns this; output is the first outreach batch sent and a 30-day re-engagement rate measured.
- Step 12: Deliver a board-ready Customer Trust Recovery Report at Month 3 — CEO presents; output documents complaint volume before and after, NPS movement, root causes fixed, and the ongoing early-warning process now embedded.
""".strip(),

        # ── 3. OPERATIONAL INEFFICIENCY ───────────────────────────────────────
        "operational inefficiency": """
[PHASE 1 — IMMEDIATE (0–48 hrs): measuring and freezing the current state]
- Step 1: Map the end-to-end operational process from order/request receipt to customer delivery in a single document — COO or Operations lead owns this within 24 hours; output is a written process map showing every step, owner, and current average time at each stage.
- Step 2: Identify the top 3 stages with the highest time loss, rework rate, or handoff failures by reviewing the last 30 days of throughput data — Analytics or Ops lead owns this; output is a ranked bottleneck list with quantified time and cost impact per bottleneck.
- Step 3: Freeze any pending headcount additions or system changes until the root cause of the bottleneck is confirmed — COO owns this; output is a written hold directive to HR and IT preventing changes that might obscure the diagnosis.

[PHASE 2 — DIAGNOSIS (Days 3–7): finding the true binding constraint]
- Step 4: Conduct time-and-motion observations on the top bottleneck stage — a senior Ops analyst shadows the process for two full days; output is a documented task-level breakdown showing where time is actually going vs. where the process says it should go.
- Step 5: Interview the 5 people closest to the bottleneck stage to surface workarounds, undocumented steps, and systemic blockers — COO or Ops lead conducts these structured sessions; output is a written list of the top 10 root causes ranked by frequency mentioned.
- Step 6: Produce a confirmed binding constraint diagnosis — COO presents to leadership by Day 7; output is a one-page memo stating the single biggest constraint, its quantified impact, and two options for addressing it.

[PHASE 3 — STABILISATION (Weeks 2–4): piloting and validating the fix]
- Step 7: Design and launch a controlled pilot of the highest-priority fix on the binding constraint — Ops lead and the affected team own this; output is a pilot running on at least 25% of volume by end of Week 2, with a clear before/after measurement protocol.
- Step 8: Measure the pilot's impact on cycle time, rework rate, and throughput and compare against the pre-pilot baseline — Analytics owns this measurement; output is a quantified result sheet showing whether the fix achieved the expected improvement.
- Step 9: Redesign the process documentation and SLAs based on pilot learnings — COO owns this; output is an updated process playbook and revised SLAs communicated to all teams by end of Week 4.

[PHASE 4 — RECOVERY (Month 2–3): embedding and scaling the improvement]
- Step 10: Roll out the validated fix across 100% of volume and retrain all affected staff on the new process — Operations lead owns this rollout; output is a completed training log and 100% adoption confirmed by end of Month 2.
- Step 11: Implement a weekly operational metrics review covering throughput, cycle time, error rate, and SLA compliance — COO chairs this; output is a standing weekly review cadence with a live dashboard.
- Step 12: Deliver a board-ready Operational Performance Report at Month 3 — COO presents; output documents baseline performance, improvements achieved, and the ongoing measurement system now in place to catch regressions early.
""".strip(),

        # ── 4. INEFFICIENT MARKETING ──────────────────────────────────────────
        "inefficient marketing": """
[PHASE 1 — IMMEDIATE (0–48 hrs): stopping waste spend]
- Step 1: Pull CAC, ROAS, and conversion rate by channel for the last 90 days — CMO or Head of Performance owns this within 24 hours; output is a channel performance table ranked by CAC efficiency, showing which channels are operating above and below acceptable thresholds.
- Step 2: Pause or hard-cap spend on any channel where CAC exceeds 2.5x target LTV with no improving trend in the last 30 days — CMO owns this decision within 24 hours; output is a written spend decision memo and revised budget allocations effective immediately.
- Step 3: Audit tracking and attribution setup to confirm whether current data is reliable — Analytics lead completes this within 48 hours; output is a written attribution audit noting any gaps, misattributions, or double-counting that are distorting channel performance data.

[PHASE 2 — DIAGNOSIS (Days 3–7): diagnosing the channel breakdown]
- Step 4: Identify whether underperformance is at the ad level (CTR declining), the landing page level (bounce rate up), or the post-lead handoff (sales conversion dropping) — CMO and Analytics jointly run this funnel decomposition; output is a ranked list of funnel breakpoints with supporting data.
- Step 5: Audit creative assets on top channels for fatigue — check frequency, CTR trend over 60 days, and audience overlap — Performance lead owns this; output is a creative fatigue report identifying which ad sets need immediate refresh.
- Step 6: Benchmark your CAC and ROAS against 2–3 direct competitors using available public data or industry reports — Strategy or CMO owns this; output by Day 7 is a benchmark comparison showing whether the underperformance is company-specific or a market-wide shift.

[PHASE 3 — STABILISATION (Weeks 2–4): rebuilding winning channels]
- Step 7: Launch 3–5 structured A/B tests on the highest-potential channel — new creative angles, audience segments, and landing page variants — Performance lead owns this; output is live tests running with a statistical significance target and a decision framework for scaling winners.
- Step 8: Rebuild the post-lead handoff process between Marketing and Sales to reduce lead decay — CMO and Sales Director co-own this; output is a revised lead SLA (time-to-contact < 4 hours) and a shared lead quality scorecard.
- Step 9: Reallocate rescued budget from paused channels into the 2–3 highest-performing channels with clear scaling guardrails — CMO owns this reallocation; output is a revised media plan with weekly spend caps and weekly performance review triggers.

[PHASE 4 — RECOVERY (Month 2–3): systematic performance governance]
- Step 10: Implement a weekly marketing performance review covering CAC, ROAS, funnel conversion, and creative performance by channel — CMO chairs this; output is a standing weekly review cadence with a live performance dashboard.
- Step 11: Build a creative production pipeline that ensures fresh ad assets are in rotation every 3–4 weeks — Creative and Performance leads co-own this; output is a creative calendar with asset briefs, production timelines, and retirement triggers.
- Step 12: Deliver a board-ready Marketing Efficiency Report at Month 3 — CMO presents; output documents CAC before and after, ROAS improvement, channels restructured, and the governance system now in place to catch degradation before it compounds.
""".strip(),

        # ── 5. FINANCIAL PRESSURE ─────────────────────────────────────────────
        "financial pressure": """
[PHASE 1 — IMMEDIATE (0–48 hrs): getting full financial visibility]
- Step 1: Build a complete P&L view — revenue, COGS, gross margin, and every operating expense line — for the last 3 months — CFO owns this within 24 hours; output is a fully reconciled P&L with gross margin and EBITDA clearly calculated for each month.
- Step 2: Categorise every cost line as: revenue-generating, operationally essential, or discretionary — CFO and COO complete this categorisation within 24 hours; output is the P&L with each line tagged and a total discretionary spend figure identified.
- Step 3: Flag any cost lines that have grown faster than revenue in the last 6 months — CFO owns this; output is a written list of cost lines growing out of proportion with revenue, with the growth rates and absolute amounts stated.

[PHASE 2 — DIAGNOSIS (Days 3–7): categorising and cutting the right costs]
- Step 4: Identify the top 3 cost lines to reduce without impairing revenue-generating functions — CFO and COO co-own this analysis; output is a cost reduction memo with specific line items, reduction amounts, implementation steps, and the revenue impact of each cut quantified.
- Step 5: Determine whether the margin pressure is structural (the business model cannot generate adequate margin at current scale) or cyclical (temporary cost or revenue shock) — CEO and CFO jointly assess this; output is a written diagnosis with supporting data.
- Step 6: Model three scenarios — base, downside, and upside — for revenue and costs over the next two quarters — CFO owns this; output by Day 7 is a three-scenario P&L model with the key assumptions stated and the decision triggers for each scenario defined.

[PHASE 3 — STABILISATION (Weeks 2–4): implementing cuts and stabilising gross margin]
- Step 7: Execute the approved cost reductions with written confirmation to affected vendors, team leads, or budget holders — CFO and relevant business leads co-own this; output is documented confirmation that each reduction has been actioned, with effective dates.
- Step 8: Review the pricing of every product or service line to identify any that are being sold below true cost or at inadequate margin — CFO and commercial lead own this; output is a pricing review with a recommendation to reprice, restructure, or discontinue each under-margin line.
- Step 9: Present revised financial projections to the board or key investors with the corrective actions and their expected impact — CEO and CFO present together; output is a board-ready financial update with the recovery trajectory clearly stated.

[PHASE 4 — RECOVERY (Month 2–3): building structural financial discipline]
- Step 10: Implement a monthly financial review cadence with full P&L, gross margin by product line, and variance analysis vs. budget — CFO chairs this; output is a standing monthly review with a live financial dashboard.
- Step 11: Introduce a monthly budget re-forecast process so that spending decisions are made against current reality, not the annual plan set 6–12 months ago — CFO owns this process; output is the first rolling re-forecast and a revised full-year outlook.
- Step 12: Deliver a board-ready Financial Health Report at Month 3 — CFO presents; output documents the margin problem identified, cuts made, gross margin recovery achieved, and the financial governance system now in place.
""".strip(),

        # ── 6. CASH FLOW ISSUE ────────────────────────────────────────────────
        "cash flow issue": """
[PHASE 1 — IMMEDIATE (0–48 hrs): mapping the 13-week cash forecast]
- Step 1: Build a week-by-week cash inflow and outflow forecast for the next 13 weeks — CFO owns this within 24 hours; output is a 13-week cash flow model with every known inflow and outflow entered, the ending cash balance for each week calculated, and the first week where the balance goes negative (if any) clearly marked.
- Step 2: Identify the 5 largest outstanding receivables and contact each debtor today with a specific payment request — CFO or Finance lead makes these calls within 24 hours; output is a written log of each conversation, the amount requested, and the committed payment date obtained.
- Step 3: Review the next 30 days of payables and identify any that can be deferred by 30 days without penalty or relationship damage — CFO owns this within 48 hours; output is a written deferral request sent to the top 3 vendors, with the deferred amounts and new due dates confirmed.

[PHASE 2 — DIAGNOSIS (Days 3–7): accelerating inflows and identifying cash sources]
- Step 4: Audit all non-core assets, excess inventory, or prepaid commitments that could be converted to cash quickly — CFO and COO jointly own this; output is a list of monetisable assets with realistic conversion values and timelines.
- Step 5: Model whether the cash problem is timing-based (receivables vs. payables mismatch) or structural (the business is loss-making and burning through capital) — CFO owns this diagnosis; output is a written one-page diagnosis confirming the root cause and the implications for the corrective action.
- Step 6: Prepare a creditor communication plan — if any payments will be missed, proactive communication preserves relationships — CFO drafts this; output by Day 7 is a communication template and a prioritised list of creditors to be contacted in advance of any missed payment.

[PHASE 3 — STABILISATION (Weeks 2–4): structural inflow acceleration and outflow management]
- Step 7: Negotiate shorter payment terms with new customers and incentivise early payment from existing ones — Finance and Sales leads co-own this; output is revised invoice terms in all new contracts and an early payment discount offer sent to the top 10 accounts.
- Step 8: Review all recurring subscriptions, retainers, and vendor contracts for services not actively being used and cancel or pause them — COO and CFO jointly own this; output is a list of cancelled or paused contracts with the monthly savings quantified.
- Step 9: Explore bridge financing options — invoice factoring, a revolving credit facility, or a short-term line of credit — if the 13-week forecast shows a negative balance — CFO leads this process; output is at least two financing options with terms and a board recommendation by end of Week 4.

[PHASE 4 — RECOVERY (Month 2–3): structural liquidity fix]
- Step 10: Implement a standing weekly cash review covering cash in, cash out, rolling 4-week forecast, and any covenant or threshold breaches — CFO chairs this; output is a weekly cash dashboard shared with the CEO and board observer.
- Step 11: Renegotiate payment terms with the top 5 suppliers to align payable cycles with receivable cycles, reducing the structural working capital gap — CFO leads these negotiations; output is revised terms with at least 3 suppliers, with the net cash impact quantified.
- Step 12: Deliver a board-ready Cash Flow Recovery Report at Month 3 — CFO presents; output documents the cash position at the start of the crisis, interventions made, current runway, and the cash management system now in place to provide 13-week forward visibility at all times.
""".strip(),

        # ── 7. TALENT RETENTION ───────────────────────────────────────────────
        "talent retention": """
[PHASE 1 — IMMEDIATE (0–48 hrs): identifying flight risks]
- Step 1: Pull all attrition data for the last 6 months segmented by team, role, tenure, and manager — HR lead owns this within 24 hours; output is a ranked breakdown showing where exits are concentrated and which managers have the highest attrition on their teams.
- Step 2: Identify your top 10% performers and anyone with rare skills or institutional knowledge — CEO and relevant team leads complete this list within 24 hours; output is a written "critical talent" list with each person's flight risk rated High / Medium / Low based on recent behaviour signals.
- Step 3: Brief all people managers on the retention situation and instruct them to have a one-on-one check-in with every direct report this week — CEO or CHRO issues this directive within 48 hours; output is a completed log of check-ins with a summary of themes surfaced.

[PHASE 2 — DIAGNOSIS (Days 3–7): diagnosing root causes]
- Step 4: Conduct structured stay interviews with your top 15 performers — CHRO or senior HRBPs run these sessions; output is a coded summary of the top 5 reasons people say they are staying and the top 5 concerns that could cause them to leave.
- Step 5: Benchmark total compensation (base, bonus, equity) against current market rates for the 5 most critical roles — HR and Finance jointly own this; output is a compensation gap analysis showing which roles are materially below market and by how much.
- Step 6: Identify the 3 managers with the highest team attrition and assess their management style, feedback culture, and workload management — CHRO leads this assessment; output by Day 7 is a written finding on whether manager quality is a primary driver, and the recommended intervention.

[PHASE 3 — STABILISATION (Weeks 2–4): deploying immediate retention levers]
- Step 7: Implement targeted compensation corrections for roles confirmed to be materially below market — CFO and CHRO co-own this decision; output is approved salary adjustments effective by end of Week 2, communicated directly and individually to affected employees.
- Step 8: Launch a transparent career pathing conversation with every high-performer — their manager has a structured 30-minute session covering the employee's 12-month growth plan — CHRO owns the framework; managers execute; output is a completed set of documented career conversations.
- Step 9: Address the top manager quality concern with direct coaching or a role reassignment for the worst-performing manager on the attrition metric — CEO makes this call; output is a written intervention plan for the manager, or a confirmed transition plan if a role change is required.

[PHASE 4 — RECOVERY (Month 2–3): structural rebuild of talent culture]
- Step 10: Implement a quarterly engagement survey (6 questions, anonymous, results shared transparently) — CHRO owns this; output is the first survey result shared with the leadership team and the top 3 improvement actions committed to publicly.
- Step 11: Build a structured recognition and reward programme that is tied to visible criteria — not manager discretion — HR and leadership co-design this; output is a live recognition programme launched with documented criteria and a monthly cadence.
- Step 12: Deliver a board-ready Talent Health Report at Month 3 — CHRO presents; output documents attrition rate before and after, flight risks addressed, compensation corrections made, manager interventions completed, and the retention monitoring system now in place.
""".strip(),

        # ── 8. PRODUCT QUALITY ISSUE ──────────────────────────────────────────
        "product quality issue": """
[PHASE 1 — IMMEDIATE (0–48 hrs): containing and stopping the defect from reaching more customers]
- Step 1: Log and triage every known defect or quality incident by severity (P0 / P1 / P2) and by frequency of occurrence — CTO or Head of QA owns this within 24 hours; output is a complete defect register with severity classifications and impacted customer counts.
- Step 2: Pause shipping, deployment, or release of any product or feature with a confirmed P0 defect — CTO and COO jointly own this stop-ship decision within 24 hours; output is a written stop-ship directive with the criteria for resuming shipment/deployment clearly stated.
- Step 3: Notify affected customers proactively with a factual, non-defensive communication that states what happened, what you are doing, and when they can expect a resolution — CEO or Head of CX owns the message; output is a drafted and approved customer notification sent within 48 hours.

[PHASE 2 — DIAGNOSIS (Days 3–7): root cause analysis]
- Step 4: Run a formal 5-Why root cause analysis on each P0 and P1 defect — the engineering or QA lead runs structured RCA sessions with all relevant contributors; output is a written root cause statement for each defect, tracing back to the process or design decision that allowed it through.
- Step 5: Audit the QA or quality control process at every stage where this defect could have been caught and was not — QA lead or an independent reviewer conducts this; output is a written gap analysis identifying every QA gate that failed to catch the defect and why.
- Step 6: Determine whether this is an isolated incident or a systemic quality failure — CTO or Quality Director assesses this; output by Day 7 is a written determination: isolated defect vs. systemic gap, with the evidence base stated.

[PHASE 3 — STABILISATION (Weeks 2–4): fixing the process and closing the defect]
- Step 7: Implement the fix for the root cause (not just the symptom) — Engineering or Operations lead owns this; output is a deployed fix with a regression test suite confirming the defect cannot recur through the same failure mode.
- Step 8: Redesign the QA gate or quality control checkpoint that failed to catch this defect — QA lead owns this redesign; output is an updated QA process document, a new test protocol, and a brief to all relevant staff.
- Step 9: Re-contact every affected customer with a resolution confirmation and, where appropriate, a goodwill gesture — CX lead owns this; output is a 100% follow-up rate confirmed with a closed-loop log and customer satisfaction confirmation rate tracked.

[PHASE 4 — RECOVERY (Month 2–3): QA hardening so this cannot recur]
- Step 10: Implement a mandatory pre-release / pre-shipment QA checklist with a sign-off requirement from a named QA owner — CTO or Quality Director owns this; output is a live checklist integrated into the release or production workflow, with the first 10 runs documented.
- Step 11: Launch a monthly quality review covering defect rates, severity distribution, resolution times, and customer complaint trends — CTO or Quality Director chairs this; output is a standing monthly review with a live quality dashboard.
- Step 12: Deliver a board-ready Quality Recovery Report at Month 3 — CTO presents; output documents the defect identified, root cause confirmed, fix deployed, QA process hardened, and the quality monitoring system now in place to catch issues before they reach customers.
""".strip(),

        # ── 9. COMPETITIVE PRESSURE ───────────────────────────────────────────
        "competitive pressure": """
[PHASE 1 — IMMEDIATE (0–48 hrs): understanding the competitive attack]
- Step 1: Document every known competitor move in the last 90 days — pricing changes, product launches, partnerships, sales hires, and marketing campaigns — Strategy or a designated competitive intelligence owner completes this within 24 hours; output is a structured competitive update memo shared with all leadership.
- Step 2: Pull your last 60 days of lost deals data and tag every loss by stated reason — Sales Director owns this; output is a ranked loss analysis showing what percentage of losses cite price, product gaps, relationship, or brand as the primary reason.
- Step 3: Brief the Sales team with factual competitive talking points so they stop losing deals to misinformation — Sales Director and CMO co-own this brief within 48 hours; output is a one-page competitive battle card for each major competitor, distributed to all quota-carrying reps.

[PHASE 2 — DIAGNOSIS (Days 3–7): finding your defensible edge]
- Step 4: Identify the 3 customer segments where you have a genuine structural advantage — switching costs, relationship depth, product fit, or unique capability — Strategy and Sales leadership jointly own this; output is a written segmentation analysis with each segment's defensibility rated.
- Step 5: Conduct 10 structured interviews with your most loyal customers to understand exactly why they stay — CX or Strategy lead owns this; output is a verbatim insight document capturing the real reasons for loyalty, usable directly in sales and marketing messaging.
- Step 6: Determine your strategic response — match, differentiate, or retreat to defensible segments — CEO makes this call; output by Day 7 is a written strategic response decision with the rationale, and a clear statement of what you will NOT do (equally important).

[PHASE 3 — STABILISATION (Weeks 2–4): choosing and committing to the response]
- Step 7: Execute the chosen competitive response — if differentiating, launch the differentiated value proposition with proof points; if matching, implement the pricing or feature change with full internal alignment — CMO and CTO co-own execution; output is the response live in market by end of Week 2.
- Step 8: Restructure sales resources to concentrate coverage on your most defensible customer segments and pull back from segments where you are structurally disadvantaged — Sales Director owns this reallocation; output is a revised territory and account priority model.
- Step 9: Launch a customer retention initiative targeting accounts at highest competitive risk — personalised outreach from a senior relationship owner with a tailored value discussion — Sales and CX co-own this; output is every at-risk account contacted with a documented outcome.

[PHASE 4 — RECOVERY (Month 2–3): arming the team and building structural resilience]
- Step 10: Implement a monthly competitive intelligence review — tracking competitor pricing, product, and positioning changes — Strategy or a designated CI owner runs this; output is a monthly competitive briefing shared with Sales, Marketing, and Product.
- Step 11: Invest in 2–3 product or service enhancements that directly address the gaps driving competitive losses — Product and CTO own the roadmap update; output is a committed product investment with a delivery timeline and a customer communication plan.
- Step 12: Deliver a board-ready Competitive Position Report at Month 3 — CEO presents; output documents the competitive threat, response strategy chosen, market share trends, retention rate in at-risk segments, and the ongoing competitive intelligence system now in place.
""".strip(),

        # ── 10. SCALING BOTTLENECK ────────────────────────────────────────────
        "scaling bottleneck": """
[PHASE 1 — IMMEDIATE (0–48 hrs): identifying the binding constraint]
- Step 1: Map the end-to-end delivery or fulfilment system and mark the single stage where throughput caps out first — COO or CTO owns this within 24 hours; output is a system map with current capacity limits quantified at each stage, and the binding constraint clearly identified.
- Step 2: Quantify the current capacity ceiling vs. current demand and the rate at which demand is growing — Analytics owns this; output is a written capacity gap statement: "At current growth rate, we will breach the capacity limit in X weeks at Y volume."
- Step 3: Implement a temporary demand throttle or waitlist mechanism to avoid customer-facing failures while the constraint is being addressed — COO and CEO jointly decide this within 48 hours; output is a customer communication explaining the waitlist or pacing, and an internal cap on new commitments.

[PHASE 2 — DIAGNOSIS (Days 3–7): quantifying the gap and evaluating options]
- Step 4: For the binding constraint, identify every possible solution — hire, automate, outsource, redesign the process, or invest in infrastructure — COO and relevant functional lead produce this list; output is an options analysis with estimated time-to-impact, cost, and risk for each option.
- Step 5: Investigate whether the constraint is in the core delivery mechanism or in a support function (onboarding, billing, compliance) that is slowing the customer journey — COO audits each support function; output is a written diagnosis confirming where the bottleneck truly sits.
- Step 6: Decide on the primary relief mechanism and initiate procurement, hiring, or engineering work immediately — CEO makes this decision by Day 7; output is a written decision with budget approved, owner assigned, and the first milestone set within 2 weeks.

[PHASE 3 — STABILISATION (Weeks 2–4): removing the constraint]
- Step 7: Execute the primary constraint relief — whether that is the first hire joining, the first automation deployed, or the outsource partner onboarded — COO owns this; output is the constraint partially relieved by end of Week 2, with a new capacity ceiling quantified.
- Step 8: Process-engineer the bottleneck stage to remove all unnecessary steps, approvals, and handoffs that slow throughput — Ops and relevant team lead own this redesign; output is a redesigned process with a documented throughput improvement target and a measurement plan.
- Step 9: Build a capacity dashboard showing real-time throughput, queue depth, and utilisation rate at each stage — Analytics builds this; output is a live dashboard reviewed daily by the COO during the constraint relief period.

[PHASE 4 — RECOVERY (Month 2–3): building to 2x current capacity]
- Step 10: Implement the full constraint relief plan to take capacity to 2x current demand — not 1.1x — COO owns this; output is a confirmed capacity level that can handle 2x current volume without degradation in quality or customer experience.
- Step 11: Build a capacity planning process that forecasts 90 days ahead and triggers investment decisions before the ceiling is breached — COO and Analytics co-own this; output is a live 90-day capacity forecast refreshed weekly.
- Step 12: Deliver a board-ready Scale Readiness Report at Month 3 — COO presents; output documents the constraint identified, the fix implemented, the new capacity ceiling, the demand forecast for the next 12 months, and the capacity planning system now in place to prevent reactive scaling.
""".strip(),

        # ── 11. LEADERSHIP MISALIGNMENT ───────────────────────────────────────
        "leadership misalignment": """
[PHASE 1 — IMMEDIATE (0–48 hrs): surfacing and documenting the disagreements]
- Step 1: Convene a structured leadership session where every executive states their top 3 priorities for the business in the next 90 days — facilitating this is the CEO's responsibility; output is a written record of each leader's stated priorities, distributed to all participants without editing.
- Step 2: Identify where priorities conflict — make the disagreements explicit and named, not implied — CEO or an external facilitator leads this session within 24 hours; output is a written conflict map showing the 3–5 most material strategic disagreements, each stated as a clear choice between two positions.
- Step 3: Communicate to all direct reports that a leadership alignment process is underway and give a date by which a unified direction will be communicated — CEO issues this message within 48 hours; output is a brief, factual internal message that prevents speculation from filling the vacuum.

[PHASE 2 — DIAGNOSIS (Days 3–7): forcing priority alignment]
- Step 4: For each material conflict, gather the data and assumptions underlying each position — the relevant functional leader prepares a one-page data brief for their position; output is a set of fact bases for each conflict, replacing opinion with evidence.
- Step 5: Run a decision session where each conflict is resolved using a pre-agreed decision framework — CEO has final authority on unresolved items; output is a written decision log for each conflict: decision made, rationale stated, dissenting views noted but not blocking.
- Step 6: Produce a 90-day strategic priorities document — maximum 3 priorities, each with a named owner, a measurable outcome, and a review date — CEO owns this document; output by Day 7 is a signed priorities document agreed by the full leadership team.

[PHASE 3 — STABILISATION (Weeks 2–4): assigning decision rights and cascading]
- Step 7: Define and document decision rights for each leadership domain — who has authority to decide, who must be consulted, and who must be informed — CEO and CHRO co-own this; output is a decision authority matrix covering all major functional and strategic decisions.
- Step 8: Cascade the agreed priorities to the second level of management with a structured brief — each C-level executive briefs their direct reports with a consistent message — COO owns the cascade process; output is a completed set of team-level briefings with confirmed receipt from all team leads.
- Step 9: Identify and address any team-level manifestations of the leadership conflict — where teams have been receiving conflicting direction — CHRO and COO jointly assess this; output is a written list of team-level conflicts with the corrective communication and re-alignment steps taken.

[PHASE 4 — RECOVERY (Month 2–3): cascading and governing the alignment]
- Step 10: Implement a monthly leadership alignment review — a structured 60-minute session reviewing priority status, emerging conflicts, and decision backlogs — CEO chairs this; output is a standing monthly meeting with a written record of decisions made and conflicts resolved.
- Step 11: Commission a leadership effectiveness assessment (360 feedback or external facilitation) to surface persistent misalignment patterns before they recur — CHRO owns this; output is an anonymised report shared with the full leadership team with agreed development actions.
- Step 12: Deliver a board-ready Leadership Alignment Report at Month 3 — CEO presents; output documents the conflicts that existed, the resolution process, the decision-making framework now in place, and evidence that the organisation is executing from a unified direction.
""".strip(),

        # ── 12. COMPLIANCE OR LEGAL RISK ──────────────────────────────────────
        "compliance or legal risk": """
[PHASE 1 — IMMEDIATE (0–48 hrs): assessing and documenting exposure]
- Step 1: Document every known compliance gap, regulatory notice, or legal exposure in a single risk register — General Counsel or CFO owns this within 24 hours; output is a risk register with each item rated by severity (material financial risk / operational risk / reputational risk) and current status (identified / under review / remediated).
- Step 2: Brief the CEO and board chair on the full risk picture — no filtering — within 24 hours; output is a factual briefing document and a verbal update to the board chair confirming the full scope of exposure.
- Step 3: Implement an immediate operational hold on any activity that knowingly continues a confirmed compliance violation — General Counsel issues this instruction within 48 hours; output is a written hold directive with the specific activities suspended until remediated.

[PHASE 2 — DIAGNOSIS (Days 3–7): engaging counsel and confirming exposure]
- Step 4: Engage specialist external legal or regulatory counsel with expertise in the relevant jurisdiction and regulatory domain — CEO and General Counsel jointly make this engagement decision within 48 hours; output is a confirmed external counsel engagement with a scope of work, retainer agreed, and first briefing scheduled.
- Step 5: Conduct a full internal compliance audit of the affected domain — external counsel and internal compliance lead co-own this; output is a written audit finding quantifying the full scope of non-compliance: duration, volume of transactions affected, and maximum financial exposure under applicable penalties.
- Step 6: Determine whether proactive disclosure to the regulator is advisable — external counsel advises on this; output by Day 7 is a written legal advice memo on disclosure timing and strategy, and the CEO's decision documented.

[PHASE 3 — STABILISATION (Weeks 2–4): building the remediation roadmap]
- Step 7: Build a compliance remediation roadmap with hard deadlines and named owners for every identified gap — General Counsel and COO co-own this; output is a project plan covering every remediation action with: the gap, the fix, the owner, the deadline, and the evidence of completion.
- Step 8: Implement immediate process controls to prevent further violations while the structural fix is built — Operations and Compliance leads jointly own this; output is a written interim control procedure deployed and signed off by all relevant team members.
- Step 9: Communicate with any affected customers, counterparties, or regulators as advised by counsel — CEO delivers this communication; output is a reviewed and approved communication sent to the required parties, with counsel sign-off confirmed.

[PHASE 4 — RECOVERY (Month 2–3): embedding compliance governance]
- Step 10: Deploy a compliance training programme covering all employees in affected functions — CHRO and General Counsel co-own this; output is a completed training log showing 100% completion rate in affected teams, with an attestation signed by each participant.
- Step 11: Implement a quarterly compliance review — a standing session chaired by the General Counsel covering regulatory changes, open risk items, and remediation status — output is a standing quarterly cadence with written minutes shared with the board audit committee.
- Step 12: Deliver a board-ready Compliance Recovery Report at Month 3 — General Counsel and CEO present together; output documents the exposure identified, remediation actions completed, interim controls deployed, evidence of no further violations, and the compliance governance system now embedded.
""".strip(),
    }

    result = steps_map.get(main)
    if result:
        return result

    # Generic fallback
    return """
[PHASE 1 — IMMEDIATE (0–48 hrs): getting full visibility]
- Step 1: Document the problem in writing with all known data points — assign a single problem owner within 24 hours; output is a one-page written problem statement with what is known, what is unknown, and what has already been tried.
- Step 2: Identify the 3 most affected stakeholders and align them on the definition of success — problem owner facilitates this within 48 hours; output is a written alignment note confirming the agreed success criteria.
- Step 3: Establish a daily stand-up for the duration of the crisis — all key decision-makers attend for 20 minutes; output is a standing meeting cadence and a shared action log updated after each session.

[PHASE 2 — DIAGNOSIS (Days 3–7): confirming root cause]
- Step 4: Gather all relevant data and run a structured root cause analysis — problem owner and Analytics lead co-own this; output is a written root cause statement with the evidence base cited and alternative explanations explicitly ruled out.
- Step 5: Test the root cause hypothesis with at least one external data point or independent perspective — an advisor, a customer interview, or a market data check; output is a confirmation or revision of the root cause.
- Step 6: Present the confirmed root cause to all decision-makers and get written agreement on the diagnosis — CEO chairs this session; output by Day 7 is a signed-off problem diagnosis that all stakeholders agree is the correct starting point for action.

[PHASE 3 — STABILISATION (Weeks 2–4): executing the fix]
- Step 7: Design and launch the primary corrective action with a clear hypothesis about the expected improvement — problem owner leads this; output is an action in motion by Week 2 with a measurement plan in place.
- Step 8: Measure the early impact of the corrective action against the success criteria defined in Phase 1 — Analytics runs the measurement; output is a data-backed progress update shared with all stakeholders.
- Step 9: Adjust the approach based on early results — problem owner makes the call on whether to continue, accelerate, or pivot — output is a written decision with rationale by end of Week 4.

[PHASE 4 — RECOVERY (Month 2–3): preventing recurrence]
- Step 10: Implement a monitoring mechanism that will detect early warning signs of this problem recurring — Analytics or Operations builds this; output is a live alert or dashboard reviewed weekly by the relevant leader.
- Step 11: Document the learnings from this episode in a post-mortem and share them with the leadership team — problem owner leads this; output is a written post-mortem covering: what happened, why, how it was fixed, and what will catch it earlier next time.
- Step 12: Deliver a board-ready recovery summary at Month 3 — CEO presents; output documents the problem, the fix, the result, and the system now in place to prevent recurrence.
""".strip()


# ── Risks builder ──────────────────────────────────────────────────────────────

def _build_risks(main: str, benchmarks: list) -> str:
    risk_map = {
        "demand decline": [
            "Treating a market-level demand shift as an internal execution problem leads to wrong fixes and wasted spend.",
            "Slow response lets competitors absorb your churned customers — recovery becomes exponentially harder after 90 days.",
            "Aggressive discounting erodes margin permanently and attracts price-sensitive customers who will leave again at the next competitive price cut.",
        ],
        "customer dissatisfaction": [
            "Unresolved complaints escalate publicly — a single viral review or social post can inflict damage that takes 12 months to repair.",
            "Customers churn before fixes are in place — the corrective action must happen in days, not weeks.",
            "Internal finger-pointing slows resolution — assign a single named owner per issue, not a committee with shared accountability.",
        ],
        "operational inefficiency": [
            "Teams revert to old habits after initial improvements — the change must be measured and managed to stick.",
            "Scope creep turns a focused fix into a long restructuring programme that never ships and demoralises the team.",
            "Without before/after metrics, you cannot confirm the improvement worked — measure first, act second.",
        ],
        "inefficient marketing": [
            "Poor attribution setup means you may be penalising the wrong channels — audit tracking before making budget decisions.",
            "Cutting spend too aggressively creates a demand vacuum that hits pipeline 60–90 days later, when you least expect it.",
            "Creative fatigue silently inflates CAC over time — treat creative refresh as a operational requirement, not an optional extra.",
        ],
        "financial pressure": [
            "Cutting costs without understanding which costs drive revenue will shrink the business, not fix it.",
            "Financial stress leaks into team morale if leadership does not communicate with honesty — people read the signals.",
            "Margin compression and cash flow problems are different issues requiring different interventions — confirm which you are solving.",
        ],
        "cash flow issue": [
            "Waiting until the bank account is near zero eliminates all negotiating leverage with vendors, lenders, and investors.",
            "Vendors notice slow payment before you tell them — proactive communication preserves the relationship; silence destroys it.",
            "Cash flow and profitability are distinct problems — a profitable business can run out of cash, and vice versa.",
        ],
        "talent retention": [
            "Exit interviews are almost always too late — by the time someone is leaving, the decision was made weeks or months ago.",
            "Counteroffers solve the symptom but rarely fix the root cause — departing employees typically leave again within 6 months.",
            "When peers leave, remaining team morale drops sharply — communicate quickly and honestly to prevent contagion.",
        ],
        "product quality issue": [
            "Shipping known defects erodes internal quality culture — it signals to engineers and operators that quality is not actually a priority.",
            "Public defect disclosures require a prepared communications response — being caught flat-footed amplifies the reputational damage.",
            "QA shortcuts to hit deadlines create compounding technical or operational debt that slows all future development and production.",
        ],
        "competitive pressure": [
            "Matching every competitor move is a race to the bottom — be selective about where you compete and decisive about where you retreat.",
            "Price wars destroy margin for all participants — only engage if you have the runway to outlast the competitor.",
            "Customer perception of your brand matters more than feature or price parity — own your differentiation story and repeat it constantly.",
        ],
        "scaling bottleneck": [
            "Adding headcount without fixing the underlying process just scales the inefficiency — and at higher cost.",
            "Infrastructure investments always take longer than estimated — start the procurement or build cycle immediately.",
            "Building to exactly 1.1x current capacity means you will hit the ceiling again in weeks — always build to at least 2x.",
        ],
        "leadership misalignment": [
            "Misalignment at the top is immediately visible to the team even when it is not discussed openly — it leaks through inconsistent decisions.",
            "Delayed resolution leads to shadow decision-making and political silos that are extremely difficult to undo once established.",
            "Consensus-seeking without a designated decision-maker leads to permanent stalemate — the CEO must be willing to decide.",
        ],
        "compliance or legal risk": [
            "Assuming internal counsel is sufficient for material regulatory risk is a costly and common mistake — bring in specialists.",
            "Fines and penalties compound if violations continue after you become aware — every day of inaction increases the exposure.",
            "Proactive disclosure to regulators is almost always better than reactive discovery — consult external counsel on timing before acting.",
        ],
    }

    risks = risk_map.get(main, [
        "Without assigned ownership, even the best plan stalls indefinitely.",
        "Over-analysis delays execution — set a decision deadline and hold to it.",
        "Misaligned stakeholders will pull the team in conflicting directions — get alignment before acting.",
    ])

    lines = [f"- {r}" for r in risks]

    if benchmarks:
        lines.append(f"- Benchmark reference: {benchmarks[0]}")

    return "\n".join(lines)
