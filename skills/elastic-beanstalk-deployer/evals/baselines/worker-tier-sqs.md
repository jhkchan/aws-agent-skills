# Baseline (no-skill) — worker-tier-sqs

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the Worker tier
> configuration namespace (aws:elasticbeanstalk:sqsd), the queue-depth
> auto scaling trigger, the lack of ELB in worker tier, and the
> READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the worker environment:

```bash
aws elasticbeanstalk create-environment \
  --application-name myapp \
  --environment-name myapp-worker \
  --solution-stack-name "64bit Amazon Linux 2023 running Python" \
  --version-label v1
```

Set the tier to worker and it should process messages from SQS.
