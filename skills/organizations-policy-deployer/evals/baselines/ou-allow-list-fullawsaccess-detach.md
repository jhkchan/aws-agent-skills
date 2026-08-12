# Baseline (no-skill) — ou-allow-list-fullawsaccess-detach

> This is the response a model produces **without** the skill
> definition. It creates the Allow-list SCP but misses the
> critical sequencing rule: FullAWSAccess must be detached
> AFTER the Allow-list is attached, or the Allow-list is
> silently redundant. Does not emit a READY_TO_DEPLOY verdict
> or note the detach step. Generated for with-skill-vs-baseline
> comparison.

---

Create the Allow-list SCP and attach it to the OU:

```bash
aws organizations create-policy \
  --content '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ec2:*","s3:*","rds:*","iam:*","logs:Describe*"],"Resource":"*"}]}' \
  --name prod-data-allowlist --type SERVICE_CONTROL_POLICY

aws organizations attach-policy --policy-id p-xxx --target-id ou-prod-data-001
```

The OU is now restricted to those services.
