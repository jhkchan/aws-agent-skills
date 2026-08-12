# Baseline (no-skill) response: eventbridge-schedule-deleted

This file captures what a generic assistant produces WITHOUT the
secrets-manager-rotation-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, symptom-to-layer triage).

---

Your secret hasn't rotated in 14 days. Since RotationEnabled is true
and RotationRules shows rate(1d), the schedule should be firing. Check
the rotation Lambda's CloudWatch logs to see if it's erroring — if
there are no log streams at all, the Lambda is never being invoked.

You might need to re-trigger rotation manually with
`aws secretsmanager rotate-secret`. If that works, the issue is likely
with the EventBridge rule that schedules the rotation. Try recreating
the rule or contacting AWS support if the schedule isn't firing.
