import io
import re
import streamlit as st
from ai_engine import generate_consulting_response, validate_consulting_input
from chart_component import render_execution_chart
from roadmap_generator import build_roadmap_from_text
from file_processor import extract_text, classify_document

st.set_page_config(page_title="ConsultMAI", layout="wide")

# ── Constants ──────────────────────────────────────────────────────────────────

FRAMEWORK_MAP = {
    "demand decline":           "McKinsey Revenue Diagnostic",
    "customer dissatisfaction": "Net Promoter Closed Loop",
    "operational inefficiency": "Theory of Constraints",
    "inefficient marketing":    "CAC/LTV Channel Audit",
    "financial pressure":       "Zero-Based Cost Review",
    "cash flow issue":          "13-Week Cash Flow Model",
    "talent retention":         "Stay Interview + Compensation Reset",
    "product quality issue":    "5-Why Root Cause + QA Hardening",
    "competitive pressure":     "Competitive Moat Analysis",
    "scaling bottleneck":       "Constraint Identification + 2x Build",
    "leadership misalignment":  "Decision Rights + Priority Cascade",
    "compliance or legal risk": "Risk Register + Remediation Roadmap",
}

HYPOTHESES_MAP = {
    "demand decline": [
        "Is the drop concentrated in one channel/region or broad-based?",
        "Has a competitor move diverted our target customers?",
        "Did product-market fit deteriorate — did our offer stop solving the problem?",
        "Did an internal change (pricing, coverage, spend) trigger the volume drop?",
    ],
    "customer dissatisfaction": [
        "Is dissatisfaction in a specific product/touchpoint or systemic?",
        "Did a recent change create a new failure point in the customer journey?",
        "Is the gap driven by overpromising in sales and marketing?",
        "Are frontline staff empowered to resolve issues at point of contact?",
    ],
    "operational inefficiency": [
        "Where is the highest concentration of delay, rework, or cost?",
        "Is this a process design failure or an execution failure?",
        "Are there redundant steps or manual handoffs that can be eliminated?",
        "Does the team lack the tools or authority to execute efficiently?",
    ],
    "inefficient marketing": [
        "Is underperformance in specific channels or is demand declining market-wide?",
        "Is our attribution model correctly measuring channel contribution?",
        "Has creative fatigue or audience saturation degraded performance?",
        "Is conversion failing at the ad, landing page, or sales handoff level?",
    ],
    "financial pressure": [
        "Is margin compression from rising costs, falling revenue, or a structural model shift?",
        "Which cost lines are growing faster than revenue?",
        "Is one product line or geography structurally unprofitable?",
        "Are pricing decisions made with full visibility of true unit economics?",
    ],
    "cash flow issue": [
        "Is the shortfall from timing mismatches or an underlying profitability problem?",
        "Which customers account for the largest outstanding receivables?",
        "Are there non-core assets or inventory that can be converted to cash?",
        "What is the true minimum operating cash per week, and how many weeks remain?",
    ],
    "talent retention": [
        "Is attrition concentrated in specific teams, tenures, or roles?",
        "Are people leaving for better pay, better growth, or better culture?",
        "Is poor management the common denominator in high-attrition teams?",
        "Has the company's pace or environment shifted away from what talent wants?",
    ],
    "product quality issue": [
        "Is this a design flaw, a process failure, or a supplier quality issue?",
        "Is this a regression or a gap that was never caught in QA?",
        "Is the failure rate concentrated in a specific batch or configuration?",
        "Does the QA process have the gates and authority to catch issues pre-release?",
    ],
    "competitive pressure": [
        "Is the competitor winning on price alone or a genuine value shift?",
        "Which segments are most at risk of switching, and which are loyal?",
        "Do we have a genuinely defensible moat, or are we competing on copyable features?",
        "Is the threat from an existing player escalating or a new entrant disrupting below?",
    ],
    "scaling bottleneck": [
        "What is the single binding constraint — people, tech, process, or capital?",
        "Is the constraint in core delivery or in support functions slowing the journey?",
        "Is the process fundamentally unscalable, or just under-resourced?",
        "Do we have enough lead time to relieve the constraint before demand hits the ceiling?",
    ],
    "leadership misalignment": [
        "Is the disagreement about direction, resource allocation, or accountability?",
        "Is this triggered by a specific event or a long-standing cultural pattern?",
        "Does the organisation have a clear decision-making framework?",
        "Has the misalignment cascaded into team-level confusion and conflicting priorities?",
    ],
    "compliance or legal risk": [
        "Is this from a process gap, a regulatory change, or a historical practice under scrutiny?",
        "What is the maximum financial penalty if the exposure becomes a formal regulatory action?",
        "Do we have internal counsel with the relevant expertise, or do we need specialists?",
        "Is this isolated to one jurisdiction/product or company-wide?",
    ],
}

FRAMEWORK_OPTIONS = [
    "Auto-detect",
    "McKinsey Revenue Diagnostic",
    "Net Promoter Closed Loop",
    "Theory of Constraints",
    "CAC/LTV Channel Audit",
    "Zero-Based Cost Review",
    "13-Week Cash Flow Model",
    "Stay Interview + Compensation Reset",
    "5-Why Root Cause + QA Hardening",
    "Competitive Moat Analysis",
    "Constraint Identification + 2x Build",
    "Decision Rights + Priority Cascade",
    "Risk Register + Remediation Roadmap",
]

# ── Session state ──────────────────────────────────────────────────────────────

if "history"          not in st.session_state: st.session_state.history          = []
if "current"          not in st.session_state: st.session_state.current          = None
if "output_mode"      not in st.session_state: st.session_state.output_mode      = "Detailed"
if "framework"        not in st.session_state: st.session_state.framework        = "Auto-detect"
if "input_error"      not in st.session_state: st.session_state.input_error      = False
if "validation_error" not in st.session_state: st.session_state.validation_error = None

# ── CSS ────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ── Layout ── */
body { overflow: hidden !important; }
[data-testid="stAppViewContainer"] > section.main { overflow-y: auto !important; overflow-x: hidden !important; }
.block-container {
    padding-top: 0.6rem !important;
    padding-bottom: 1rem !important;
    overflow: visible !important;
}

/* ── Page background ── */
[data-testid="stAppViewContainer"] { background: #C8E6F7; }
[data-testid="stSidebar"] { background: #E8ECF0; border-right: 1px solid #B8CFE0; }

/* ── Fix white-on-white text ── */
[data-testid="stWidgetLabel"] p,
[data-testid="stMarkdownContainer"] p,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] span,
label { color: #334155 !important; }

/* ── File uploader — + circle icon ── */
[data-testid="stFileUploaderDropzone"] {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
    min-height: unset !important;
}
[data-testid="stFileUploaderDropzone"] div { display: none !important; }
[data-testid="stFileUploaderDropzone"] button {
    width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    border-radius: 50% !important;
    border: 1.5px solid #94A3B8 !important;
    background: transparent !important;
    font-size: 0 !important;
    padding: 0 !important;
    cursor: pointer !important;
}
[data-testid="stFileUploaderDropzone"] button::after {
    content: '+';
    font-size: 1.3rem;
    color: #64748B;
    font-weight: 300;
    display: block;
    line-height: 36px;
}
[data-testid="stFileUploaderDropzone"] button:hover {
    border-color: #3B8FD4 !important;
    background: #E4EDF8 !important;
}
[data-testid="stFileUploaderDropzone"] button:hover::after { color: #3B8FD4; }
[data-testid="stFileUploadedFiles"] {
    font-size: 0.76rem !important;
    color: #334155 !important;
}

/* ── Input strip card (st.container border=True) ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 20px !important;
    border: 1.5px solid #B8CFE0 !important;
    box-shadow: 0 4px 18px rgba(0,0,0,0.07) !important;
    background: #E8ECF0 !important;
    margin: 6px 32px 28px 32px !important;
    padding: 4px 8px !important;
}

/* ── Chat bubble ── */
.user-bubble {
    background: #3B8FD4;
    color: #FFFFFF;
    border-radius: 12px 12px 4px 12px;
    padding: 10px 14px;
    font-size: 0.92rem;
    line-height: 1.55;
    margin-bottom: 6px;
}
.context-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    padding: 6px 0 10px 0;
    border-bottom: 1px solid #B8CFE0;
    margin-bottom: 6px;
}
.context-chip-dark {
    display: inline-block;
    background: #3B8FD4;
    color: #FFFFFF;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 0.80rem;
    font-weight: 700;
}
.framework-chip {
    display: inline-block;
    background: #EEF2F5;
    border: 1px solid #3B8FD4;
    color: #1A2C3D;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 0.80rem;
    font-weight: 600;
}

/* ── Panel labels ── */
.panel-label {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #94A3B8;
    margin-bottom: 14px;
}

/* ── Thinking panel components ── */
.think-problem-node {
    background: #3B8FD4;
    color: #FFFFFF;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 1.0rem;
    font-weight: 600;
    margin-bottom: 8px;
}
.think-arrow {
    text-align: center;
    color: #8AAEC8;
    font-size: 1.2rem;
    margin: 4px 0;
}
.think-hypothesis {
    background: #EEF2F5;
    border-left: 3px solid #3B8FD4;
    border-radius: 0 6px 6px 0;
    padding: 6px 12px;
    font-size: 0.90rem;
    color: #1A2C3D;
    margin-bottom: 5px;
}
.think-framework-badge {
    display: inline-block;
    background: #EEF2F5;
    border: 1px solid #3B8FD4;
    color: #1A2C3D;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.88rem;
    font-weight: 600;
    margin: 10px 0 12px 0;
}
.think-section-label {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #8AAEC8;
    margin: 14px 0 5px 0;
}
.think-input-echo {
    background: #EEF2F5;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 0.90rem;
    color: #4A6D8C;
    font-style: italic;
    border: 1px solid #B8CFE0;
    max-height: 80px;
    overflow: hidden;
}

/* ── Urgency badge ── */
.urgency-badge {
    display: inline-block;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 0.70rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}
.urgency-critical { background: #FEE2E2; color: #991B1B; }
.urgency-high     { background: #FEF3C7; color: #92400E; }
.urgency-medium   { background: #DBEAFE; color: #1E40AF; }
.urgency-low      { background: #DCFCE7; color: #166534; }

/* ── Metric pill ── */
.metric-pill {
    display: inline-block;
    background: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-radius: 12px;
    padding: 2px 9px;
    font-size: 0.72rem;
    color: #334155;
    margin: 2px 3px 2px 0;
}

/* ── Industry / stage chip ── */
.context-chip {
    display: inline-block;
    background: #EEF2F5;
    border: 1px solid #B8CFE0;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 0.70rem;
    font-weight: 600;
    color: #3B8FD4;
    margin-right: 5px;
}

/* ── Output section labels ── */
.out-section-label {
    font-size: 0.80rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #8AAEC8;
    margin: 18px 0 6px 0;
    border-bottom: 1px solid #B8CFE0;
    padding-bottom: 4px;
}

/* ── Situation box ── */
.situation-box {
    background: #EEF2F5;
    border-left: 4px solid #3B8FD4;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    font-size: 0.97rem;
    color: #1A2C3D;
    line-height: 1.6;
}

/* ── Priority flow ── */
.flow-wrap {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin: 4px 0;
}
.flow-step-box {
    background: #3B8FD4;
    color: #FFFFFF;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.92rem;
    font-weight: 500;
    text-align: center;
}
.flow-down {
    text-align: center;
    color: #8AAEC8;
    font-size: 1.1rem;
    line-height: 1.2;
    margin: 0;
}

/* ── Key components ── */
.component-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 7px;
}
.component-bullet {
    width: 7px;
    height: 7px;
    background: #3B8FD4;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
}

/* ── Phase header ── */
.phase-header {
    background: linear-gradient(90deg, #3B8FD4 0%, #5AA8E6 100%);
    color: #FFFFFF;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 0.86rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 20px 0 8px 0;
}
.phase-number {
    opacity: 0.65;
    margin-right: 6px;
}

/* ── Step rows ── */
.step-row {
    background: #EEF2F5;
    border-left: 3px solid #3B8FD4;
    border-radius: 0 6px 6px 0;
    padding: 8px 12px;
    margin-bottom: 6px;
}
.step-label {
    font-size: 0.84rem;
    font-weight: 700;
    color: #3B8FD4;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.step-action {
    font-size: 0.95rem;
    color: #1A2C3D;
}
.step-output-label {
    font-size: 0.80rem;
    color: #4A6D8C;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 3px;
}
.step-output-value {
    font-size: 0.91rem;
    color: #3B8FD4;
    font-style: italic;
}

/* ── Rejection card ── */
.rejection-card {
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    border-radius: 10px;
    padding: 16px 18px;
    margin-top: 8px;
}
.rejection-title {
    font-size: 0.90rem;
    font-weight: 700;
    color: #9A3412;
    margin-bottom: 6px;
}
.rejection-body {
    font-size: 0.80rem;
    color: #431407;
    line-height: 1.5;
    margin-bottom: 12px;
}
.rejection-type-badge {
    display: inline-block;
    background: #FEF3C7;
    border: 1px solid #F59E0B;
    color: #78350F;
    border-radius: 8px;
    padding: 2px 10px;
    font-size: 0.70rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 10px;
}
.accepts-label {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94A3B8;
    margin-bottom: 5px;
}
.accepts-item {
    font-size: 0.78rem;
    color: #334155;
    padding: 3px 0 3px 8px;
    border-left: 2px solid #22C55E;
    margin-bottom: 3px;
}

/* ── Hero bar ── */
.hero-bar {
    background: linear-gradient(90deg, #3B8FD4 0%, #5AA8E6 100%);
    border-radius: 10px;
    padding: 7px 20px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
}
.hero-title {
    color: #FFFFFF;
    font-size: 1.0rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}
.hero-sub {
    color: rgba(255,255,255,0.78);
    font-size: 0.78rem;
    margin-top: 1px;
}

/* ── Primary button ── */
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(90deg, #3B8FD4 0%, #5AA8E6 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 10px 0 !important;
    width: 100% !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    opacity: 0.88 !important;
}

/* ── Textarea ── */
textarea {
    border-radius: 8px !important;
    border: 1px solid #C2D4EA !important;
    font-size: 0.87rem !important;
}
textarea:focus {
    border-color: #3B8FD4 !important;
    box-shadow: 0 0 0 2px rgba(59,143,212,0.15) !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    border-radius: 8px !important;
    border: 1px solid #C2D4EA !important;
    font-size: 0.84rem !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: #F2F6FC !important;
    border: 1px solid #C2D4EA !important;
    border-radius: 8px !important;
    color: #1A2C3D !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
}

/* ── Sidebar buttons ── */
[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: #F2F6FC !important;
    border: 1px solid #C2D4EA !important;
    border-radius: 8px !important;
    color: #1A2C3D !important;
    font-size: 0.80rem !important;
    text-align: left !important;
    padding: 8px 10px !important;
    width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background: #E4EDF8 !important;
    border-color: #3B8FD4 !important;
}

/* ── Empty states ── */
.output-empty {
    color: #94A3B8;
    font-size: 0.88rem;
    padding: 40px 0;
    text-align: center;
    line-height: 1.8;
}
.think-empty {
    color: #94A3B8;
    font-size: 0.83rem;
    padding: 30px 0;
    text-align: center;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _process_uploaded_file(uploaded_file):
    """Returns (text, file_type_label, accepted, rejection_label, rejection_reason)."""
    if uploaded_file is None:
        return "", "", True, None, None
    text, file_type = extract_text(uploaded_file)
    accepted, label, reason = classify_document(text, uploaded_file.name)
    return text, file_type, accepted, label, reason


def _parse_sections(text: str) -> dict:
    parts = re.split(r'\*\*([^*]+):\*\*', text)
    sections = {}
    for i in range(1, len(parts) - 1, 2):
        sections[parts[i].strip()] = parts[i + 1].strip()
    return sections


def _urgency_style(urgency: str) -> str:
    return {
        "critical": "urgency-critical",
        "high":     "urgency-high",
        "medium":   "urgency-medium",
        "low":      "urgency-low",
    }.get(urgency, "urgency-medium")


def _resolve_framework(selected: str, analysis: dict) -> str:
    if selected and selected != "Auto-detect":
        return selected
    return FRAMEWORK_MAP.get(analysis.get("main_issue", ""), "Structured Problem Decomposition")


def _build_markdown_export(result: str, analysis: dict) -> str:
    lines = ["# ConsultMAI — Structured Analysis", ""]
    lines.append(f"**Main Issue:** {analysis.get('main_issue', '').title()}")
    lines.append(f"**Industry:** {analysis.get('industry', 'general').title()}")
    lines.append(f"**Stage:** {analysis.get('company_stage', 'unknown').title()}")
    if analysis.get("metrics"):
        lines.append(f"**Detected Metrics:** {', '.join(analysis['metrics'].values())}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(result)
    return "\n".join(lines)


# ── Rejection card renderer ────────────────────────────────────────────────────

def _render_rejection_card(rejection_type: str, reason: str):
    type_labels = {
        "resume":   "CV / Resume",
        "academic": "Academic Assignment",
        "off_topic": "Off-Topic Input",
    }
    type_label = type_labels.get(rejection_type, "Invalid Input")

    accepts = [
        "Operational problems — delivery delays, process breakdowns, quality failures",
        "Financial challenges — margin compression, cash flow issues, burn rate concerns",
        "Commercial problems — demand decline, competitive pressure, CAC inefficiency",
        "Talent and leadership issues — attrition, misalignment, culture breakdown",
        "Compliance and legal exposure — regulatory gaps, audit findings, legal risk",
        "Scaling challenges — capacity constraints, infrastructure gaps, rapid growth",
    ]
    accepts_html = "".join(f'<div class="accepts-item">{a}</div>' for a in accepts)

    st.markdown(f"""
<div class="rejection-card">
  <div class="rejection-type-badge">{type_label}</div>
  <div class="rejection-title">ConsultMAI cannot process this input</div>
  <div class="rejection-body">{reason}</div>
  <div class="accepts-label">ConsultMAI is designed for:</div>
  {accepts_html}
</div>
""", unsafe_allow_html=True)


# ── Thinking panel renderer ────────────────────────────────────────────────────

def _render_thinking_panel(current: dict):
    result_text = current["output"]
    analysis    = current["analysis"]
    main_issue  = analysis.get("main_issue", "")
    framework   = _resolve_framework(st.session_state.framework, analysis)
    hypotheses  = HYPOTHESES_MAP.get(main_issue, analysis.get("root_causes", []))
    industry    = analysis.get("industry", "general")
    stage       = analysis.get("company_stage", "unknown")
    urgency     = analysis.get("urgency", "medium")
    metrics     = analysis.get("metrics", {})
    raw_input   = analysis.get("raw_input", "")

    # Problem node
    st.markdown(
        f'<div class="think-problem-node">{main_issue.title() if main_issue else "Problem Identified"}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="think-arrow">↓</div>', unsafe_allow_html=True)

    # Hypotheses
    st.markdown('<div class="think-section-label">Root Cause Hypotheses</div>', unsafe_allow_html=True)
    for h in hypotheses[:4]:
        st.markdown(f'<div class="think-hypothesis">{h}</div>', unsafe_allow_html=True)

    st.markdown('<div class="think-arrow">↓</div>', unsafe_allow_html=True)

    # Framework badge
    st.markdown(
        f'<div class="think-framework-badge">{framework}</div>',
        unsafe_allow_html=True,
    )

    # Context row
    st.markdown('<div class="think-section-label">Context</div>', unsafe_allow_html=True)
    industry_html = f'<span class="context-chip">{industry.upper()}</span>' if industry not in ("general", "") else ""
    stage_html    = f'<span class="context-chip">{stage.title()}</span>'    if stage not in ("unknown", "")   else ""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">'
        f'{industry_html}{stage_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Detected metrics
    if metrics:
        st.markdown('<div class="think-section-label">Signals Detected</div>', unsafe_allow_html=True)
        pills = "".join(f'<span class="metric-pill">{v}</span>' for v in metrics.values())
        st.markdown(f'<div>{pills}</div>', unsafe_allow_html=True)

    # Input echo
    st.markdown('<div class="think-section-label">Input</div>', unsafe_allow_html=True)
    echo = raw_input[:220] + ("…" if len(raw_input) > 220 else "")
    st.markdown(f'<div class="think-input-echo">{echo}</div>', unsafe_allow_html=True)


# ── Output panel renderer ──────────────────────────────────────────────────────

def _render_output_panel(current: dict, output_mode: str):
    result_text = current["output"]
    analysis    = current["analysis"]
    sections    = _parse_sections(result_text)

    show_situation  = True
    show_flow       = True
    show_components = output_mode in ("Detailed", "Executive")
    show_steps      = output_mode in ("Detailed", "Executive")

    # ── Situation ──
    if show_situation:
        body = sections.get("Situation", "")
        if body:
            st.markdown('<div class="out-section-label">Situation</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="situation-box">{body}</div>', unsafe_allow_html=True)

    # ── Priority Flow ──
    if show_flow:
        body = sections.get("Priority Flow", "")
        if body:
            st.markdown('<div class="out-section-label">Priority Flow</div>', unsafe_allow_html=True)
            steps = [s.strip() for s in re.split(r'\s*->\s*', body) if s.strip()]
            if steps:
                nodes_html = ""
                for idx, step in enumerate(steps):
                    nodes_html += f'<div class="flow-step-box">{step}</div>'
                    if idx < len(steps) - 1:
                        nodes_html += '<div class="flow-down">↓</div>'
                st.markdown(
                    f'<div class="flow-wrap">{nodes_html}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f'<div class="situation-box">{body}</div>', unsafe_allow_html=True)

    # ── Key Components ──
    if show_components:
        body = sections.get("Key Components", "")
        if body:
            st.markdown('<div class="out-section-label">Key Components</div>', unsafe_allow_html=True)
            for line in body.split("\n"):
                line = line.strip().lstrip("-").strip()
                if line:
                    st.markdown(
                        f'<div class="component-row">'
                        f'<div class="component-bullet"></div>'
                        f'<div style="font-size:0.95rem;color:#1E293B;">{line}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # ── Execution Steps ──
    if show_steps:
        body = sections.get("Execution Steps", "")
        if body:
            st.markdown('<div class="out-section-label">Execution Steps</div>', unsafe_allow_html=True)
            for line in body.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue

                # Phase header
                if stripped.startswith("[PHASE"):
                    label = stripped.strip("[]")
                    st.markdown(
                        f'<div class="phase-header">{label}</div>',
                        unsafe_allow_html=True,
                    )
                    continue

                # Step line
                if stripped.startswith("- Step"):
                    content = stripped[2:]  # remove "- "
                    # Try | separator (real LLM format)
                    pipe_parts = [p.strip() for p in content.split("|")]
                    if len(pipe_parts) == 4:
                        action_raw  = pipe_parts[0]
                        owner_raw   = pipe_parts[1]
                        due_raw     = pipe_parts[2]
                        output_raw  = pipe_parts[3]

                        # Parse "Step N: action text"
                        colon_idx = action_raw.find(":")
                        if colon_idx != -1:
                            step_label  = action_raw[:colon_idx].strip()
                            action_text = action_raw[colon_idx + 1:].strip()
                        else:
                            step_label  = "Step"
                            action_text = action_raw

                        owner_val  = owner_raw.replace("Owner:", "").strip()
                        due_val    = due_raw.replace("Due:", "").strip()
                        output_val = output_raw.replace("Output:", "").strip()

                        st.markdown(f"""
<div class="step-row">
  <div>
    <span class="step-label">{step_label}</span>
    <span class="step-action"> — {action_text}</span>
  </div>
  <div style="margin-top:5px;display:flex;gap:16px;flex-wrap:wrap;">
    <span><span class="step-output-label">Owner</span>&nbsp;<span class="step-output-value">{owner_val}</span></span>
    <span><span class="step-output-label">Due</span>&nbsp;<span class="step-output-value">{due_val}</span></span>
    <span><span class="step-output-label">Output</span>&nbsp;<span class="step-output-value">{output_val}</span></span>
  </div>
</div>""", unsafe_allow_html=True)

                    else:
                        # Mock format — rich prose, no | separators
                        colon_idx = content.find(":")
                        if colon_idx != -1:
                            step_label  = content[:colon_idx].strip()
                            action_text = content[colon_idx + 1:].strip()
                        else:
                            step_label  = "Step"
                            action_text = content

                        st.markdown(
                            f'<div class="step-row">'
                            f'<span class="step-label">{step_label}</span>'
                            f'<span class="step-action"> — {action_text}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

    # ── Export ──
    md_content = _build_markdown_export(result_text, analysis)
    st.download_button(
        label="Export to Markdown",
        data=md_content.encode("utf-8"),
        file_name="consultmai_analysis.md",
        mime="text/markdown",
        use_container_width=True,
    )


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="font-size:1.1rem;font-weight:700;color:#3B8FD4;margin-bottom:4px;">ConsultMAI</div>'
        '<div style="font-size:0.85rem;color:#4A6D8C;margin-bottom:16px;">Turn complexity into execution clarity</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.history:
        st.markdown(
            '<div style="font-size:0.80rem;font-weight:700;text-transform:uppercase;'
            'letter-spacing:0.09em;color:#64748B;margin-bottom:8px;">'
            f'History ({len(st.session_state.history)})</div>',
            unsafe_allow_html=True,
        )
        for i, entry in enumerate(reversed(st.session_state.history)):
            label = entry["analysis"].get("main_issue", "Analysis").title()
            snippet = entry["input"][:45] + ("…" if len(entry["input"]) > 45 else "")
            if st.button(f"{label} — {snippet}", key=f"hist_{i}", use_container_width=True):
                st.session_state.current = entry
                st.session_state.validation_error = None
                st.rerun()

        if st.button("Clear History", use_container_width=True):
            st.session_state.history = []
            st.session_state.current = None
            st.session_state.validation_error = None
            st.rerun()
    else:
        st.markdown(
            '<div class="think-empty">Your analysis history will appear here.</div>',
            unsafe_allow_html=True,
        )


# ── Hero bar ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero-bar">
  <div>
    <div class="hero-title">ConsultMAI</div>
    <div class="hero-sub">Senior consulting framework — instantly applied to your business problem</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Content area: single panel → splits into two when roadmap exists ───────────

def _render_chat_thread(height: int):
    box = st.container(height=height, border=False)
    with box:
        if not st.session_state.history:
            st.markdown(
                '<div class="think-empty">'
                'Describe a business problem below and click <strong>Structure It</strong>.<br><br>'
                'Be specific — include numbers, timelines, and what you have already tried.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            for entry in st.session_state.history:
                analysis   = entry["analysis"]
                industry   = analysis.get("industry", "")
                stage      = analysis.get("company_stage", "")
                metrics    = analysis.get("metrics", {})
                framework  = _resolve_framework(st.session_state.framework, analysis)
                main_issue = analysis.get("main_issue", "")

                st.markdown(
                    f'<div class="user-bubble">{entry["input"]}</div>',
                    unsafe_allow_html=True,
                )
                chips = ""
                if main_issue:
                    chips += f'<span class="context-chip-dark">{main_issue.title()}</span>'
                if industry and industry not in ("general", ""):
                    chips += f'<span class="context-chip">{industry.upper()}</span>'
                if stage and stage not in ("unknown", ""):
                    chips += f'<span class="context-chip">{stage.title()}</span>'
                for v in list(metrics.values())[:3]:
                    chips += f'<span class="metric-pill">{v}</span>'
                chips += f'<span class="framework-chip">{framework}</span>'
                st.markdown(
                    f'<div class="context-strip">{chips}</div>',
                    unsafe_allow_html=True,
                )


if st.session_state.current is None:
    # ── Before first submit: single wide chat panel ──
    st.markdown('<div class="panel-label">Your Situation</div>', unsafe_allow_html=True)
    _render_chat_thread(height=400)
    if st.session_state.validation_error:
        _render_rejection_card(
            st.session_state.validation_error["type"],
            st.session_state.validation_error["reason"],
        )
else:
    # ── After submit: chat left, roadmap right ──
    left_col, right_col = st.columns([4, 6], gap="medium")

    with left_col:
        st.markdown('<div class="panel-label">Your Situation</div>', unsafe_allow_html=True)
        _render_chat_thread(height=390)
        if st.session_state.validation_error:
            _render_rejection_card(
                st.session_state.validation_error["type"],
                st.session_state.validation_error["reason"],
            )

    with right_col:
        st.markdown('<div class="panel-label">Execution Roadmap</div>', unsafe_allow_html=True)
        roadmap = st.session_state.current.get("roadmap")
        if roadmap:
            render_execution_chart(roadmap)
        else:
            roadmap_box = st.container(height=390, border=False)
            with roadmap_box:
                _render_output_panel(st.session_state.current, "Detailed")
        with st.expander("View Full Analysis"):
            scroll_box = st.container(height=480, border=False)
            with scroll_box:
                _render_output_panel(st.session_state.current, "Detailed")


# ── Full-width input strip — below both panels, with footer margin ──────────────

with st.container(border=True):
    user_text = st.text_area(
        label="Describe your situation",
        label_visibility="collapsed",
        placeholder="Describe what is happening — include numbers, timelines, context.",
        height=80,
        key="user_input_area",
    )

    plus_col, fw_col, _, send_col = st.columns([1, 4, 3, 3])

    with plus_col:
        uploaded_file = st.file_uploader(
            "attach",
            type=None,
            label_visibility="collapsed",
            key="file_upload",
        )

    with fw_col:
        selected_framework = st.selectbox(
            "Framework",
            options=FRAMEWORK_OPTIONS,
            index=FRAMEWORK_OPTIONS.index(st.session_state.framework)
                if st.session_state.framework in FRAMEWORK_OPTIONS else 0,
            label_visibility="collapsed",
            key="framework_select",
        )
        st.session_state.framework = selected_framework

    with send_col:
        submit = st.button("Structure It →", type="primary", use_container_width=True)

    if uploaded_file is not None:
        _, detected_type = extract_text(uploaded_file)
        if detected_type:
            st.markdown(
                f'<div style="font-size:0.72rem;color:#4A6878;padding:2px 0 0 4px;">'
                f'&#128206; {detected_type} attached</div>',
                unsafe_allow_html=True,
            )

if st.session_state.input_error:
    st.warning("Please describe your situation before submitting.")


# ── Submit handler ─────────────────────────────────────────────────────────────

if submit:
    file_text, file_type, file_accepted, file_reject_label, file_reject_reason = \
        _process_uploaded_file(uploaded_file)

    # Block on file-level rejection before even combining text
    if uploaded_file is not None and not file_accepted:
        st.session_state.validation_error = {
            "type": file_reject_label,
            "reason": file_reject_reason,
        }
        st.session_state.current = None
        st.rerun()

    combined = (user_text or "").strip()
    if file_text:
        combined = combined + "\n\n" + file_text.strip()
    combined = combined.strip()

    if not combined:
        st.session_state.input_error = True
        st.rerun()

    st.session_state.input_error = False

    is_valid, rejection_type, reason = validate_consulting_input(combined)

    if not is_valid:
        st.session_state.validation_error = {"type": rejection_type, "reason": reason}
        st.session_state.current = None
        st.rerun()

    st.session_state.validation_error = None

    with st.spinner("Structuring your situation…"):
        result_text, analysis = generate_consulting_response(combined)

    roadmap = build_roadmap_from_text(result_text, analysis)
    entry = {
        "input":    combined,
        "output":   result_text,
        "analysis": analysis,
        "roadmap":  roadmap,
    }
    st.session_state.history.append(entry)
    st.session_state.current = entry
    st.rerun()
