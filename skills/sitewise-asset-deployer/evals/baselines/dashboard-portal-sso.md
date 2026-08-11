# Baseline (no-skill) — dashboard-portal-sso

> This is the response a model produces **without** the skill
> definition. It creates the portal and dashboard but misses the
> Identity Center requirement for SSO portals, the alarm duration
> parameter (without it the alarm fires on every spike), the access
> policy requirement (users authenticate but see no projects), and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create the portal and dashboard:

```bash
aws iotsitewise create-portal --portal-name "Acme Plant Portal"
aws iotsitewise create-dashboard --dashboard-name "Compressor Overview"
```

Then add an alarm on Pressure.
