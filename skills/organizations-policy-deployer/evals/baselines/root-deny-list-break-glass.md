# Baseline (no-skill) — root-deny-list-break-glass

> This is the response a model produces **without** the skill
> definition. It produces a `create-policy` and `attach-policy`
> call but misses the FullAWSAccess strategy, the break-glass
> OU carve-out requirement, the inheritance intersection
> behavior, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Sure, here's the SCP:

```bash
aws organizations create-policy \
  --content '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"organizations:LeaveOrganization","Resource":"*"}]}' \
  --name root-guardrails --type SERVICE_CONTROL_POLICY

aws organizations attach-policy --policy-id p-xxx --target-id r-xxxx
```

That covers the org.
