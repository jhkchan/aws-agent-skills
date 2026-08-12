# Baseline (no-skill) response: pattern-detail-type-mismatch

This file captures what a generic assistant produces WITHOUT the
eventbridge-rule-not-firing-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, symptom-to-layer triage).

---

Your EventBridge rule isn't firing. Since PutEvents returns 200, the
event is being received. The issue is probably with your event pattern.
Check that the source and detail-type match the event. You can use
`test-event-pattern` to verify.

Looking at your pattern, `detail-type: ["Order Created"]` should match
the event. The detail.status also looks right. Maybe check if the
target Lambda has the right permissions? Or try recreating the rule.
