# Baseline (no-skill) — ca-deletion-waiting-period

> This is the response a model produces **without** the skill
> definition. It deletes the CA but does not mention the mandatory
> 7-30 day waiting period, does not document the restore capability,
> does not note that existing certificates remain valid but cannot be
> revoked after permanent deletion, and does not emit the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Delete the CA:

```bash
aws acm-pca delete-certificate-authority \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/dddd-eeee-ffff
```

The CA will be deleted.
