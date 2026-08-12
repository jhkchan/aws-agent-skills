# Baseline (no-skill) — multi-ou-inherited-intersection

> This is the response a model produces **without** the skill
> definition. It creates and attaches the Deny SCP at the
> parent OU but does not trace the inheritance intersection at
> the child account, does not show the OU chain walk, and does
> not emit a READY_TO_DEPLOY verdict. Generated for
> with-skill-vs-baseline comparison.

---

Attach the SCP at OU_Prod:

```bash
aws organizations create-policy \
  --content '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":["iam:DeleteRole","iam:DetachRolePolicy"],"Resource":"*"}]}' \
  --name prod-deny-root-tamper --type SERVICE_CONTROL_POLICY

aws organizations attach-policy --policy-id p-xxx --target-id ou-prod-001
```

Account 111122223311 inherits this automatically.
