# Baseline (no-skill) response: stage-cache-enablement

This file captures what a generic assistant produces WITHOUT the
apigateway-throttle-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, cache hit ratio projection,
TTL sizing, dollar savings estimate, CONFIRM gate).

---

Your product catalog API has a lot of repeated GET requests that return
the same data. Since the catalog only changes hourly, you should enable
caching on the API Gateway stage.

At 70% idempotent GETs with 95ms integration latency, caching would
eliminate a significant portion of your Lambda invocations.

```
aws apigateway update-stage \
  --rest-api-id <api-id> \
  --stage-name prod \
  --patch-operations op=replace,path=/caching/enabled,value=true
```

Set the TTL to 3600 seconds (1 hour) to match your catalog update
frequency. This should reduce your Lambda costs noticeably.
