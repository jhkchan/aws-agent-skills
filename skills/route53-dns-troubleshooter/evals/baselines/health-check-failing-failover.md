# Baseline (no-skill) response: health-check-failing-failover

This file captures what a generic assistant produces WITHOUT the
route53-dns-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

Your failover routing is always returning the secondary record. This
means your health check is failing. Check the health check in the
Route 53 console and make sure it's monitoring the right endpoint.

The health check shows Unhealthy with a 404 error. You should fix the
endpoint so it returns a 200 status code. Also make sure the health
check path is correct.
