# Baseline (no-skill) response: weighted-no-healthcheck

This file captures what a generic assistant produces WITHOUT the
route53-record-auditor skill loaded.

---

These are weighted records splitting traffic 50/50 between two endpoints.
Neither has a health check. You should consider adding health checks so
Route 53 can stop sending traffic to an endpoint that's down.

DNSSEC is enabled on the zone which is good. The TTLs are consistent.
