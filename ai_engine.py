def structure_problem(user_input):

    problem = user_input.lower()

    issues = []

    if any(word in problem for word in ["drop", "decline", "decrease", "fall"]):
        issues.append(("demand decline", 3))

    if any(word in problem for word in ["complaint", "bad", "issue", "dissatisfied"]):
        issues.append(("customer dissatisfaction", 2))

    if any(word in problem for word in ["delivery", "delay", "slow"]):
        issues.append(("operational inefficiency", 2))

    if any(word in problem for word in ["marketing", "ads", "spend", "cac"]):
        issues.append(("inefficient marketing", 1))

    if any(word in problem for word in ["profit", "loss", "cost"]):
        issues.append(("financial issue", 2))

    # sort by importance score
    issues = sorted(issues, key=lambda x: x[1], reverse=True)

    if issues:
        main_issue = issues[0][0]
    else:
        main_issue = "unclear problem"

    issue_list = [i[0] for i in issues]

    return f"""
🧠 KEY DRIVER:
👉 {main_issue.upper()}

⚖️ PRIORITY ORDER:
{", ".join(issue_list) if issue_list else "Need better input"}

🛣️ ACTION ITINERARY (THIS IS WHAT YOU WANTED 🔥):

DAY 0–2:
- Deep dive into {main_issue}
- Identify exact root cause using available data

WEEK 1:
- Launch immediate fix for {main_issue}
- Example: if demand → offers, if ops → fix delays

WEEK 2–4:
- Address second priority: {issue_list[1] if len(issue_list) > 1 else "N/A"}
- Stabilize performance

MONTH 2+:
- Fix remaining issues: {", ".join(issue_list[2:]) if len(issue_list) > 2 else "None"}
- Build long-term system improvements

🎯 STRATEGY:
Focus = 1 problem at a time → not everything together.
"""