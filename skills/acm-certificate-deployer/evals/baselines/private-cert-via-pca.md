# Baseline (no-skill) — private-cert-via-pca

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the private
> certificate NOT-browser-trusted caveat, the PCA health dependency
> for renewal, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

To request a private certificate:

1. Request from ACM with the PCA ARN:
```bash
aws acm request-certificate \
  --domain-name internal.api.example.com \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/abc-123 \
  --validation-method DNS
```

2. Add the DNS validation record.

That should work for your mTLS setup.
