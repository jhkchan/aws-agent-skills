# Baseline (no-skill) — group-sso-auto-assignment

> This is the response a model produces **without** the skill
> definition. It assigns the permission set but misses the provisioning
> step (the assignment does not take effect without
> provision-permission-set), the three-way binding concept, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Assign the permission set:

```bash
aws sso-admin create-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-12345 \
  --target-id 123456789012 --target-type AWS_ACCOUNT \
  --permission-set-arn <arn> \
  --principal-type GROUP --principal-id SecurityTeam
```

The group should now have access.
