# Baseline (no-skill) response: config-gap-no-archive

This file captures what a generic assistant produces WITHOUT the
eventbridge-bus-policy-auditor skill loaded — the contrast that proves
the skill adds structure (replay-capability reasoning, deterministic
CONFIG_GAP verdict).

---

The bus configuration looks mostly good — the policy is scoped, there's
a KMS key, and the target has a dead-letter queue. But there's no
archive configured. This means you can't replay events if something
goes wrong. You should create an archive for this bus.
