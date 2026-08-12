# Baseline (no-skill) — allow-list-without-fullawsaccess-detach

> This is the response a model produces **without** the skill
> definition. It attaches the Allow-list SCP without flagging
> that FullAWSAccess is still attached at the same entity,
> which makes the Allow-list silently redundant (the
> intersection still permits everything FullAWSAccess permits).
> Does not emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Sure:

```bash
aws organizations create-policy \
  --content '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ec2:*","s3:*"],"Resource":"*"}]}' \
  --name prod-allowlist --type SERVICE_CONTROL_POLICY

aws organizations attach-policy --policy-id p-xxx --target-id ou-prod-apps-001
```

The OU is now restricted to EC2 and S3.
