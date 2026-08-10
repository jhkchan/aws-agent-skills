# Baseline (no-skill) response: 503-wrong-health-check-path

This file captures what a generic assistant produces WITHOUT the
alb-5xx-troubleshooter skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

Your ALB is returning 503, which means it has no healthy targets. Check
the target group and you'll probably see all your targets are unhealthy.
This usually means the health check is failing. Look at the health check
configuration and make sure the path and port are correct.

The health check path might be wrong — if your app serves health on a
different path than what's configured, all targets will show as unhealthy.
Try updating the health check path to match what your application actually
serves.
