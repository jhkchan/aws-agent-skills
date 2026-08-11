# Baseline (no-skill) — org-conformance-pack-deployment

> This is the response a model produces **without** the skill definition.
> It deploys a conformance pack at the account level rather than the
> organization level (PutConformancePack instead of
> PutOrganizationConformancePack), missing the org-wide deployment to all
> accounts, and does not include input parameters or verification commands.

---

Here's how to deploy a conformance pack:

```bash
aws configservice put-conformance-pack \
  --conformance-pack-name OperationalBestPractices-for-EC2 \
  --template-s3-uri s3://config-templates-123456789012/ec2-best-practices.yaml \
  --region us-east-1
```

This creates the conformance pack on your account.
