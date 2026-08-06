# Baseline (no-skill) response: ttl-inconsistency-weighted

This file captures what a generic assistant produces WITHOUT the
route53-record-auditor skill loaded.

---

These weighted records have health checks which is good. The stable
record has a TTL of 300 and the canary has 3600. You might want to make
these the same to keep caching consistent.

The traffic split is 90/10 which looks reasonable for a canary deployment.
