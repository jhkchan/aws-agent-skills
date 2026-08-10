# Baseline (no-skill) response: 503-stage-throttle-exceeded

This file captures what a generic assistant produces WITHOUT the
apigateway-5xx-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

A 503 error means the service is unavailable, usually because of
throttling. Your API Gateway stage probably has rate limits configured
that are being exceeded during your traffic spike.

You can increase the throttling limits in the API Gateway console or via
the CLI. Look at the stage settings and increase the rate limit and burst
limit. Also consider setting up a usage plan with API keys to control
traffic per client.
