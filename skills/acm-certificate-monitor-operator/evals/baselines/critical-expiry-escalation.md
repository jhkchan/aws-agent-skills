# Baseline (no-skill) — critical-expiry-escalation

> This is the response a model produces **without** the skill
> definition. It checks the certificate status but misses the CAA
> record investigation (the #1 renewal blocker), DNS validation record
> verification, service attachment confirmation, and the
> OPERATION_COMPLETED report format. Generated for with-skill-vs-
> baseline comparison.

---

Your certificate is about to expire. Check the ACM console to see
if renewal is in progress. You can describe it with:

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/crit-001
```

If renewal is pending, it should complete automatically. Make sure
the certificate is attached to a supported service.
