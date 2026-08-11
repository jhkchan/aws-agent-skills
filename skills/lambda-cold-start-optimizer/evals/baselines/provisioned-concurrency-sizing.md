# Baseline (no-skill) response: provisioned-concurrency-sizing

This file captures what a generic assistant produces WITHOUT the
lambda-cold-start-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, provisioned
concurrency sizing from ConcurrentExecutions percentiles, latency
impact estimate, CONFIRM gate).

---

Your Node.js function has cold-start latency issues. The InitDuration
p95 is 2800 ms which is well above your 500 ms SLO. Since this is a
synchronous API behind API Gateway, you should consider using
provisioned concurrency to keep execution environments warm and
eliminate cold starts entirely.

You can set up provisioned concurrency with:

```
aws lambda put-provisioned-concurrency-config --function-name fn-provisioned-concurrency-sizing --qualifier prod --provisioned-concurrent-executions 20
```

You might need to experiment with the right number. Start with 20 and
adjust based on your traffic. Note that this will add cost since you're
paying for idle capacity.
