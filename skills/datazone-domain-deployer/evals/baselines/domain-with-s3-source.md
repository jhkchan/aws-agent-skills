# Baseline (no-skill) — domain-with-s3-source

> This is the response a model produces **without** the skill
> definition. It creates the domain and data source but misses the
> cross-account IAM role trust policy requirement (the #1 missing
> prerequisite), the glossary-term-driven subscription policies
> (treating glossary as just labels), the request-approve model
> (assuming auto-approval), the SSO requirement, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the domain:

```bash
aws datazone create-domain --name analytics-domain
```

Add a project and data source:

```bash
aws datazone create-project --domain-id <id> --name customer-analytics
aws datazone create-data-source --name customer-events-s3 --type S3
```

Add glossary terms and you should be good. Subscriptions should
work automatically once the data source is connected.
