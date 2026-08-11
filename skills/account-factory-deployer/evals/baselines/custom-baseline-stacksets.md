# Baseline (no-skill) — custom-baseline-stacksets

> This is the response a model produces **without** the skill
> definition. It creates the account but misses that custom StackSets
> need a service-managed permission model and auto-deployment
> configuration, does not verify the default Control Tower baseline
> alongside the custom StackSet, and does not emit the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the account and a custom StackSet:

```bash
aws organizations create-account \
  --email aws+prod-ml@company.com --account-name ml-platform-prod

aws cloudformation create-stack-set \
  --stack-set-name "CustomBaseline-VPC" \
  --template-body file://vpc.yaml
```

The account should get the VPC.
