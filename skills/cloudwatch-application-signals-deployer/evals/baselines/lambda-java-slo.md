# Baseline (no-skill) — lambda-java-slo

> This is the response a model produces **without** the skill definition.
> It produces generic Lambda layer-attach instructions but misses the
> explicit IAM policy verification, the AWS_SERVICE_NAME env var, the
> architecture-specific layer ARN, and the multi-window burn-rate
> alarm thresholds (5m/14.4x, 1h/6x, 6h/3x).

---

For Lambda, attach the ADOT Java layer to your function:

```bash
aws lambda update-function-configuration \
  --function-name auth-api \
  --layers arn:aws:lambda:us-east-1:901920570463:layer:aws-otel-java-wrapper-amd64:19
```

Make sure your execution role has X-Ray permissions. Then create
your SLO and alarm.
