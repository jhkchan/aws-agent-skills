# Baseline (no-skill) — security-group-content-audit

> This is the response a model produces **without** the skill
> definition. It creates a security group policy but does not distinguish
> common vs content audit mode, does not recommend monitor-only for safe
> rollout, and misses the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create a security group policy:

```bash
aws fms put-policy \
  --policy-name org-sg-audit-no-ssh-open \
  --security-service-policy-data Type=SECURITY_GROUPS_COMMON
```

That should enforce the security groups you need.
