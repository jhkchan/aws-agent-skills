# Baseline (no-skill) response: public-bus-weak-source-ip

This file captures what a generic assistant produces WITHOUT the
eventbridge-bus-policy-auditor skill loaded — the contrast that proves
the skill adds structure (weak-condition detection, 0.0.0.0/0
internet-CIDR reasoning, deterministic PUBLIC_BUS verdict).

---

The bus policy grants events:PutEvents to all principals with an IP
restriction. The other settings (KMS, DLQ, archive) look good. The IP
condition is set to 0.0.0.0/0 which covers all IP addresses, so it
doesn't actually restrict anything. You should tighten the IP range or
remove the wildcard principal.
