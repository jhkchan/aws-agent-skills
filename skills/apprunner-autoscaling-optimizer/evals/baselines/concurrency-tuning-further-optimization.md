# Baseline (no-skill) response: concurrency-tuning-further-optimization

This file captures what a generic assistant produces WITHOUT the
apprunner-autoscaling-optimizer skill loaded.

---

Your App Runner service `prod-api-service` has an average of 2.3 instances
with concurrency 100. Your CPU utilization is 35% and memory is 30%, which
looks healthy. The service costs $1,200/month.

You could try increasing the concurrency setting to reduce the number of
instances. To update the auto-scaling configuration:

```bash
aws apprunner create-auto-scaling-configuration \
  --auto-scaling-configuration-name prod-api-asg-v2 \
  --min-size 1 --max-size 25 --concurrency 150

aws apprunner update-service \
  --service-arn <arn> \
  --auto-scaling-configuration-arn <new-arn>
```

Monitor the latency after the change.
