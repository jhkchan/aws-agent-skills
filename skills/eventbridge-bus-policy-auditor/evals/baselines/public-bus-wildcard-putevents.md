# Baseline (no-skill) response: public-bus-wildcard-putevents

This file captures what a generic assistant produces WITHOUT the
eventbridge-bus-policy-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated FINDINGS,
event-injection reasoning, per-dimension remediation).

---

This EventBridge bus policy grants `events:PutEvents` to all AWS
principals (`Principal: {"AWS": "*"}`). This means anyone can publish
events to your bus. You should restrict this.

The bus also has no KMS key configured, no dead-letter queue on the
rule target, and no archive. These are also issues to address.
