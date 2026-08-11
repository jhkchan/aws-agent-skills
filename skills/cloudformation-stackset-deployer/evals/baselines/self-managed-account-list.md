# Baseline (no-skill) — self-managed-account-list

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the admin/execution
> role trust chain, the fact that create-stack-set does NOT deploy
> instances, operation preferences, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the StackSet:

```bash
aws cloudformation create-stack-set \
  --stack-set-name config-baseline \
  --template-body file://config-baseline.yaml \
  --parameters ParameterKey=LogLevel,ParameterValue=INFO
```

Deploy to your accounts:

```bash
aws cloudformation create-stack-instances \
  --stack-set-name config-baseline \
  --deployment-targets Accounts="111111111111,222222222222,333333333333" \
  --regions "us-east-1,eu-west-1"
```

You should be good to go.
