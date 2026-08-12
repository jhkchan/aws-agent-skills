# Baseline (no-skill) — caa-record-conflict

> This is the response a model produces **without** the skill
> definition. It sees the FAILED renewal status but does not
> investigate CAA records (the root cause), does not check DNS
> validation records, and suggests re-requesting the certificate
> rather than fixing the CAA conflict. Does not emit a REVIEW_REQUIRED
> verdict. Generated for with-skill-vs-baseline comparison.

---

Your renewal failed. Try re-requesting the certificate:

```bash
aws acm request-certificate \
  --domain-name www.example.com \
  --validation-method DNS
```

Or check the ACM console for more details about why renewal failed.
Make sure the certificate is still attached to your ALB.
