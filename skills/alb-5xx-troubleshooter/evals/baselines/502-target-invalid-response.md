# Baseline (no-skill) response: 502-target-invalid-response

This file captures what a generic assistant produces WITHOUT the
alb-5xx-troubleshooter skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

You're getting intermittent 502 errors, which suggests your application
is occasionally crashing or returning invalid responses. The health check
passes because it's a simple endpoint, but the actual application is
failing under real traffic.

Check your application logs for errors like segfaults or crashes. You
might need to fix a bug in the HTTP server or increase the memory/CPU
on your instances. Also consider adding retry logic or circuit breakers
to handle these intermittent failures gracefully.
