# Diagnostic Commands (load on demand) — CloudFormation StackSet Deployer

Deployment and lifecycle command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Step 8 — update and delete operations (moved from SKILL.md)

**Update the StackSet (propagates to all instances):**

```bash
aws cloudformation update-stack-set \
  --stack-set-name my-stackset \
  --template-url https://s3.amazonaws.com/my-bucket/template-v2.yaml \
  --parameters ParameterKey=ExampleParam,ParameterValue=newvalue \
  --operation-preferences FailureTolerancePercentage=5,MaxConcurrentPercentage=20
```

- `update-stack-set` propagates the new template/parameters to ALL
  existing stack instances, respecting operation preferences.
- For SERVICE_MANAGED + managed execution, drifted instances are
  auto-reconciled as part of the update.

**Delete specific instances:**

```bash
aws cloudformation delete-stack-instances \
  --stack-set-name my-stackset \
  --deployment-targets Accounts="111111111111" \
  --regions "us-east-1" \
  --retain-stacks false
```

`--retain-stacks false` (default) deletes underlying stacks; `true`
orphans them (remain but unmanaged).

**Delete the StackSet (after all instances removed):**

```bash
aws cloudformation delete-stack-set --stack-set-name my-stackset
```

You MUST delete all stack instances first (`delete-stack-instances`),
then delete the StackSet. Calling `delete-stack-set` while instances
exist fails.
