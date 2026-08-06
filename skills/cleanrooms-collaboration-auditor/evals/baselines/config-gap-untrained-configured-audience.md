# Baseline (no-skill) response: config-gap-untrained-configured-audience

This file captures what a generic assistant produces WITHOUT the
cleanrooms-collaboration-auditor skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, enumerated
FINDINGS, specific remediation, multi-party reasoning).

---

The collaboration has two ACTIVE members, DP enabled, low epsilon
spend, and aggregate constraints set. The collaboration is configured
for audience activation with a configuredAudienceModelArn.

The configured audience model is in CREATE_FAILED state, which means
the training job failed. Audience activation queries will not work
until this is fixed. You should investigate the training failure and
retrain the model.
