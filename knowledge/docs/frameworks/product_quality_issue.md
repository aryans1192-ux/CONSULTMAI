# Framework: Product Quality Issue
**Framework Name:** 5-Why Root Cause + QA Hardening
**Problem Type:** product quality issue
**Tags:** bug, defect, broken, malfunction, crash, recall, error, poor quality, QA failure

## Hypothesis Tree — Root Cause Questions
- Is the defect or quality failure driven by a design flaw, a manufacturing or engineering process failure, or a supplier quality issue?
- Is this a regression — something that was working and has broken — or a gap that was never caught in initial QA?
- What is the failure rate, and is it concentrated in a specific batch, cohort, or configuration?
- Does the QA process have the right gates, test coverage, and escalation authority to catch issues before they reach customers?

## Priority Flow
Contain and stop shipping defects → Root cause analysis → Fix the process → Harden QA

## Execution Playbook

### PHASE 1 — IMMEDIATE (0–48 hrs): containing and stopping the defect
- Step 1: Log and triage every known defect or quality incident by severity (P0 / P1 / P2) and by frequency of occurrence — CTO or Head of QA owns this within 24 hours; output is a complete defect register with severity classifications and impacted customer counts.
- Step 2: Pause shipping, deployment, or release of any product or feature with a confirmed P0 defect — CTO and COO jointly own this stop-ship decision within 24 hours; output is a written stop-ship directive with the criteria for resuming shipment/deployment clearly stated.
- Step 3: Notify affected customers proactively with a factual, non-defensive communication that states what happened, what you are doing, and when they can expect a resolution — CEO or Head of CX owns the message; output is a drafted and approved customer notification sent within 48 hours.

### PHASE 2 — DIAGNOSIS (Days 3–7): root cause analysis
- Step 4: Run a formal 5-Why root cause analysis on each P0 and P1 defect — the engineering or QA lead runs structured RCA sessions with all relevant contributors; output is a written root cause statement for each defect, tracing back to the process or design decision that allowed it through.
- Step 5: Audit the QA or quality control process at every stage where this defect could have been caught and was not — QA lead or an independent reviewer conducts this; output is a written gap analysis identifying every QA gate that failed to catch the defect and why.
- Step 6: Determine whether this is an isolated incident or a systemic quality failure — CTO or Quality Director assesses this; output by Day 7 is a written determination: isolated defect vs. systemic gap, with the evidence base stated.

### PHASE 3 — STABILISATION (Weeks 2–4): fixing the process and closing the defect
- Step 7: Implement the fix for the root cause (not just the symptom) — Engineering or Operations lead owns this; output is a deployed fix with a regression test suite confirming the defect cannot recur through the same failure mode.
- Step 8: Redesign the QA gate or quality control checkpoint that failed to catch this defect — QA lead owns this redesign; output is an updated QA process document, a new test protocol, and a brief to all relevant staff.
- Step 9: Re-contact every affected customer with a resolution confirmation and, where appropriate, a goodwill gesture — CX lead owns this; output is a 100% follow-up rate confirmed with a closed-loop log and customer satisfaction confirmation rate tracked.

### PHASE 4 — RECOVERY (Month 2–3): QA hardening so this cannot recur
- Step 10: Implement a mandatory pre-release / pre-shipment QA checklist with a sign-off requirement from a named QA owner — CTO or Quality Director owns this; output is a live checklist integrated into the release or production workflow, with the first 10 runs documented.
- Step 11: Launch a monthly quality review covering defect rates, severity distribution, resolution times, and customer complaint trends — CTO or Quality Director chairs this; output is a standing monthly review with a live quality dashboard.
- Step 12: Deliver a board-ready Quality Recovery Report at Month 3 — CTO presents; output documents the defect identified, root cause confirmed, fix deployed, QA process hardened, and the quality monitoring system now in place to catch issues before they reach customers.
