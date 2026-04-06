import re
import streamlit as st
from ai_engine import generate_consulting_response

st.set_page_config(page_title="Structured Execution AI", layout="wide")

# ── Session state init ─────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "prefill" not in st.session_state:
    st.session_state.prefill = ""


# ── Output renderer (defined first so it can be called in the layout) ──────────

def _render_output(text, analysis):
    parts = re.split(r'\*\*([^*]+):\*\*', text)
    sections = {}
    for i in range(1, len(parts) - 1, 2):
        sections[parts[i].strip()] = parts[i + 1].strip()

    known = ["Situation", "Key Components", "Priority Flow", "Execution Steps", "Notes / Risks"]

    for name in known:
        body = sections.get(name, "")
        if not body:
            continue

        if name == "Situation":
            st.info(body)

        elif name == "Key Components":
            st.markdown("**Key Components**")
            st.markdown(body)

        elif name == "Priority Flow":
            st.markdown("**Priority Flow**")
            steps = [s.strip() for s in re.split(r'\s*->\s*', body) if s.strip()]
            if steps:
                cols = st.columns(len(steps))
                for col, step in zip(cols, steps):
                    col.markdown(
                        f'<div style="background:#1e1e1e;border:1px solid #333;border-radius:8px;'
                        f'padding:10px 14px;font-size:0.85rem;text-align:center;">{step}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(body)

        elif name == "Execution Steps":
            st.markdown("**Execution Steps**")
            for line in body.split("\n"):
                line = line.strip()
                if line.startswith("- Step"):
                    line_parts = line[2:].split(":", 1)
                    if len(line_parts) == 2:
                        label, action = line_parts
                        st.markdown(
                            f'<div style="background:#1a1a2e;border-left:3px solid #4a90d9;'
                            f'padding:8px 14px;border-radius:0 6px 6px 0;margin-bottom:6px;">'
                            f'<span style="color:#4a90d9;font-weight:600;font-size:0.82rem;">{label.strip()}</span>'
                            f'<span style="color:#ddd;font-size:0.9rem;"> — {action.strip()}</span></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(line)

        elif name == "Notes / Risks":
            urgency = analysis.get("urgency", "medium")
            if urgency in ("critical", "high"):
                st.error("**Notes / Risks**\n\n" + body)
            else:
                st.warning("**Notes / Risks**\n\n" + body)

        st.markdown("")


# ── Sidebar ────────────────────────────────────────────────────────────────────
EXAMPLES = [
    "Our sales dropped 30% in the last 3 months and we don't know why. We're also getting more complaints than usual.",
    "We raised $2M but our burn rate is $180k/month and we have no clear path to profitability.",
    "Three senior engineers quit in the last 6 weeks. The remaining team seems disengaged and we're missing deadlines.",
    "We're growing fast but our delivery times have gone from 2 days to 8 days and customers are starting to leave.",
    "Our main competitor just slashed prices by 40%. We're losing deals we used to win easily and don't know how to respond.",
]

with st.sidebar:
    st.markdown("### Examples")
    st.caption("Click to load a scenario")
    for example in EXAMPLES:
        if st.button(example[:60] + "...", use_container_width=True):
            st.session_state.prefill = example

    if st.session_state.history:
        st.divider()
        st.markdown(f"### History ({len(st.session_state.history)})")
        for entry in reversed(st.session_state.history):
            with st.expander(entry["input"][:50] + "...", expanded=False):
                st.caption(
                    f"Urgency: {entry['analysis']['urgency'].upper()}  |  "
                    f"{len(entry['analysis']['issue_list'])} issue(s) detected"
                )
                st.markdown(entry["output"])


# ── Header ─────────────────────────────────────────────────────────────────────
st.title("Structured Execution AI")
st.caption("Turn complexity into execution clarity")
st.divider()

# ── Main layout ────────────────────────────────────────────────────────────────
col_in, col_out = st.columns([2, 3], gap="large")

with col_in:
    st.markdown("#### Describe your situation")
    user_input = st.text_area(
        label="input",
        label_visibility="collapsed",
        placeholder="Describe what's happening — be specific. Include numbers if you have them.",
        value=st.session_state.prefill,
        height=220,
    )

    run = st.button("Structure It", type="primary", use_container_width=True)

    # Clear prefill after it's been loaded into the text area
    if st.session_state.prefill:
        st.session_state.prefill = ""

with col_out:
    if run:
        if not user_input.strip():
            st.warning("Please describe your situation first.")
        else:
            with st.spinner("Structuring..."):
                result, analysis = generate_consulting_response(user_input)

            st.session_state.history.append({
                "input":    user_input,
                "output":   result,
                "analysis": analysis,
            })

            # ── Metadata badges ───────────────────────────────────────────────
            urgency_colors = {
                "critical": "#c0392b",
                "high":     "#e67e22",
                "medium":   "#2980b9",
                "low":      "#27ae60",
            }
            color = urgency_colors.get(analysis["urgency"], "#555")

            badge = (
                f'<span style="background:{color};color:white;padding:4px 12px;'
                f'border-radius:12px;font-weight:600;font-size:0.82rem;letter-spacing:0.05em;">'
                f'{analysis["urgency"].upper()}</span>'
            )
            tags = " ".join(
                f'<span style="background:#2d2d2d;color:#ccc;padding:3px 9px;'
                f'border-radius:8px;font-size:0.76rem;">{tag}</span>'
                for tag in analysis["issue_list"]
            )
            st.markdown(badge + "&nbsp;&nbsp;" + tags, unsafe_allow_html=True)

            if analysis["metrics"]:
                st.caption("Detected: " + "  |  ".join(analysis["metrics"].values()))

            st.divider()

            _render_output(result, analysis)

    elif not st.session_state.history:
        st.markdown(
            '<div style="color:#666;padding:40px 0;font-size:0.95rem;line-height:1.8;">'
            'Your structured output will appear here.<br><br>'
            'Try one of the examples in the sidebar, or describe your own situation on the left.'
            '</div>',
            unsafe_allow_html=True,
        )
