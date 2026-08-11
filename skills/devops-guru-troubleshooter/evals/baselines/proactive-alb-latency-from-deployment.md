# Baseline (no-skill) — proactive-alb-latency-from-deployment

> This is the response a model produces **without** the skill definition.
> It reads the insight description and recommends scaling out, missing
> the change-correlation with the CodeDeploy deployment and the RDS
> connection pool exhaustion signal. Generated for with-skill-vs-
> baseline comparison.

---

The DevOps Guru insight shows increased latency on your ALB. Here's
what to do:

1. The recommendation says to investigate the backend service. Check
   the ALB target group health:
```bash
aws elbv2 describe-target-health --target-group-arn <arn>
```

2. Consider scaling out the backend Auto Scaling Group to handle the
   load:
```bash
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name my-asg \
  --desired-capacity 10 --max-size 20
```

3. Add a CloudWatch alarm on TargetResponseTime to catch future
   spikes.

The latency should improve once the backend scales out.
