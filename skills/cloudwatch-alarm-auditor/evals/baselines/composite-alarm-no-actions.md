# Baseline (no-skill) response: composite-alarm-no-actions

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, blind-spot reasoning).

---

This composite alarm triggers when either high-cpu-prod or high-memory-prod
fires. The Rule expression looks correct using OR logic.

The composite alarm doesn't have its own actions, but since the child alarms
have AlarmActions configured, notifications should still go out when either
condition is met. You could add actions to the composite if you want a
separate escalation path.
