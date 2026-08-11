# Baseline (no-skill) — operation-preferences-tuning

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but accepts default operation
> preferences (no failure tolerance or concurrency tuning), misses
> the CAPABILITY_AUTO_EXPAND requirement, and omits the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create and deploy the StackSet:

```bash
aws cloudformation create-stack-set \
  --stack-set-name ssm-patch-baseline \
  --template-url s3://templates/patch-baseline.yaml

aws cloudformation create-stack-instances \
  --stack-set-name ssm-patch-baseline \
  --deployment-targets OrganizationalUnitIds="ou-def-11223344" \
  --regions "us-east-1,us-east-2,us-west-2,eu-west-1"
```

The default operation preferences should be fine for this.
