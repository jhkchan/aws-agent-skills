# Baseline (no-skill) response: prod-drift-notify-only

This file captures what a generic assistant produces WITHOUT the
drift-detection-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, production protection
gates, approval requirement, blast-radius classification).

---

For production stack drift, you should set up drift detection but
probably not auto-remediate since it's a critical stack. Just
detect and notify.

You can use EventBridge to schedule a daily detect-stack-drift call
and send an SNS notification when drift is found.

The drifted resources (SecurityGroups, IAM policy, ALB listener) should
be reviewed by an operator before any changes are made. If the changes
were intentional hotfixes, you might want to update the template to
match. If they're unintentional, you can create a change-set to revert.

Be careful with production stacks — don't just re-apply the template
without checking what changed.
