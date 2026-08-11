# Baseline (no-skill) — oversampled-default-rule

> This is the response a model produces **without** the skill definition.
> It does NOT flag the cost risk of setting the Default sampling rule to
> 100% on a 5000 req/s service. The model proceeds with the operator's
> request, which would generate ~432M traces/day.

---

Here's how to set up X-Ray tracing on your EKS Node.js API:

```bash
npm install aws-xray-sdk-core
```

Deploy the X-Ray daemon as a DaemonSet in your EKS cluster. Then set
the Default sampling rule to 100%:

```bash
aws xray update-sampling-rule --cli-input-json '{
  "SamplingRuleUpdate": {
    "RuleName": "Default",
    "FixedRate": 1.0,
    "ReservoirSize": 1
  }
}'
```

This will trace every request as you requested.
