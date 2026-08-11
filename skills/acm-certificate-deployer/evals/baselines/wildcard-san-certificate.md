# Baseline (no-skill) — wildcard-san-certificate

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the multi-level
> wildcard limitation (*.example.com does NOT cover
> *.api.example.com), the DNS validation CNAME lifecycle, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

To create an ACM certificate with multiple domains:

1. Request the certificate:
```bash
aws acm request-certificate \
  --domain-name "*.example.com" \
  --subject-alternative-names "example.com" "*.api.example.com" \
  --validation-method DNS
```

2. Add the validation records to Route53.

3. Wait for issuance.

That should cover it.
