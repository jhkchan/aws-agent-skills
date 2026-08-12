# Baseline (no-skill) — profile-role-mapping

> This is the response a model produces **without** the skill
> definition. It shows the create-profile command but misses that
> session policies only RESTRICT permissions (never expand them), does
> not explain the role-passthrough alternative, and does not emit the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

To create a profile:

```bash
aws rolesanywhere create-profile \
  --name ci-runner-profile \
  --trust-anchor-id ta-aaa111222 \
  --role-arns arn:aws:iam::123456789012:role/RolesAnywhereCIRunner
```

Add your session policy and you should be good.
