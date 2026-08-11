# Baseline (no-skill) — missing-service-role

> This is the response a model produces **without** the skill
> definition. It attempts environment creation without verifying that
> the service role exists, missing the prerequisite entirely. The
> command would fail at runtime with an IAM error. Generated for
> with-skill-vs-baseline comparison.

---

Create the environment:

```bash
aws elasticbeanstalk create-environment \
  --application-name myapp \
  --environment-name myapp-prod \
  --solution-stack-name "64bit Amazon Linux 2023 running Node.js 20" \
  --version-label v2
```

This should create the environment. If there's an error, check the
IAM permissions.
