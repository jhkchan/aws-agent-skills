# Baseline (no-skill) — missing-trusted-access

> This is the response a model produces **without** the skill
> definition. It blindly emits create-stack-set commands without
> verifying the Organizations trusted access prerequisite, missing
> the `InvalidOperationException` that will occur at runtime.
> Generated for with-skill-vs-baseline comparison.

---

Here's how to create your StackSet:

```bash
aws cloudformation create-stack-set \
  --stack-set-name my-stackset \
  --template-body file://baseline.yaml \
  --permission-model SERVICE_MANAGED

aws cloudformation create-stack-instances \
  --stack-set-name my-stackset \
  --deployment-targets OrganizationalUnitIds="ou-fail-99887766" \
  --regions "us-east-1"
```

That should deploy it.
