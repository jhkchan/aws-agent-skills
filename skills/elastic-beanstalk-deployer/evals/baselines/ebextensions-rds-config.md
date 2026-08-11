# Baseline (no-skill) — ebextensions-rds-config

> This is the response a model produces **without** the skill
> definition. It mentions .ebextensions but misses the DeletionPolicy
> Retain requirement (RDS is terminated with the environment without
> it), the lexicographic ordering constraint, the container_commands
> leader_only semantics, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the environment with the source bundle. The .ebextensions in
the bundle will create the RDS instance automatically.

```bash
aws elasticbeanstalk create-environment \
  --application-name myapp \
  --environment-name myapp-api \
  --version-label v1
```

The .config files in .ebextensions should handle the RDS creation.
