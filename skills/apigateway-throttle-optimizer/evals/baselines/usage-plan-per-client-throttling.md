# Baseline (no-skill) response: usage-plan-per-client-throttling

This file captures what a generic assistant produces WITHOUT the
apigateway-throttle-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, per-client throttle math,
tiered usage plan design, CONFIRM gate, client coordination warning).

---

Your mobile app client is consuming 80% of your API throttle capacity,
causing 429 errors for your other clients. You should set up usage plans
with API keys to enforce per-client rate limits.

Create usage plans for different client tiers and associate API keys
with each client:

```
aws apigateway create-usage-plan --name "mobile-app" --throttle burstLimit=1000,rateLimit=1600
aws apigateway create-usage-plan --name "web-dashboard" --throttle burstLimit=200,rateLimit=200
```

Then create API keys for each client and associate them with the usage
plans. Your clients will need to send the x-api-key header with each
request.
