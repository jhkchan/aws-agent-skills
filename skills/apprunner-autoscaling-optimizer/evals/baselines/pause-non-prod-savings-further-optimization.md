# Baseline (no-skill) response: pause-non-prod-savings-further-optimization

This file captures what a generic assistant produces WITHOUT the
apprunner-autoscaling-optimizer skill loaded.

---

Your dev service costs $720/month and only gets traffic during business
hours. You can save money by pausing it when not in use:

```bash
aws apprunner pause-service --service-arn <arn>
```

To resume:
```bash
aws apprunner resume-service --service-arn <arn>
```

You could automate this with EventBridge or a Lambda function to pause at
night and resume in the morning.
