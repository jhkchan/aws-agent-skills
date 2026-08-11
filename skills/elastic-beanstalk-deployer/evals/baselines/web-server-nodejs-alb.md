# Baseline (no-skill) — web-server-nodejs-alb

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the immutable deployment
> policy recommendation (defaults to all-at-once), the service role and
> instance profile prerequisites, the enhanced health requirement for
> managed updates, the Amazon Linux 2023 platform branch selection, and
> the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the environment:

```bash
aws elasticbeanstalk create-environment \
  --application-name myapp \
  --environment-name myapp-prod \
  --solution-stack-name "64bit Amazon Linux 2023 running Node.js" \
  --version-label v2
```

That should create the environment with the Node.js platform.
