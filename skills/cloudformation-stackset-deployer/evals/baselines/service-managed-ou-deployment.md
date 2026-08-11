# Baseline (no-skill) — service-managed-ou-deployment

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the permission model
> immutability, the two-call sequence (create-stack-set + create-
> stack-instances), the management-account skip, operation preference
> tuning, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to create a CloudFormation StackSet:

```bash
aws cloudformation create-stack-set \
  --stack-set-name baseline-iam-roles \
  --template-url s3://my-bucket/templates/baseline-iam.yaml \
  --capabilities CAPABILITY_IAM
```

Then deploy to your OU:

```bash
aws cloudformation create-stack-instances \
  --stack-set-name baseline-iam-roles \
  --deployment-targets OrganizationalUnitIds="ou-abc-12345678" \
  --regions "us-east-1,us-west-2,eu-west-1"
```

That should work.
