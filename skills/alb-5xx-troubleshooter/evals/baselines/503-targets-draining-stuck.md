# Baseline (no-skill) response: 503-targets-draining-stuck

This file captures what a generic assistant produces WITHOUT the
alb-5xx-troubleshooter skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

A 503 during a deployment usually means you deregistered all your old
targets before the new ones were ready. The ALB has no healthy targets
to send traffic to. Wait for the new targets to pass their health checks
and they should start receiving traffic.

For future deployments, make sure to register new targets before
deregistering the old ones, or use a rolling deployment strategy so
there are always healthy targets available.
