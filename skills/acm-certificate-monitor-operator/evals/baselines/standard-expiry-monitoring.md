# Baseline (no-skill) — standard-expiry-monitoring

> This is the response a model produces **without** the skill
> definition. It creates a single alarm without tiering (misses the
> warning/critical two-tier approach), does not check renewal
> eligibility or DNS validation, does not check CAA records, and omits
> the OPERATION_COMPLETED report format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to set up expiry monitoring for your certs:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "cert-expiry" \
  --namespace AWS/CertificateManager \
  --metric-name DaysToExpiry \
  --threshold 30 \
  --comparison-operator LessThanThreshold
```

Set up an SNS topic for notifications and subscribe your team.
