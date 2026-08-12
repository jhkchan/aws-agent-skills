# Baseline (no-skill) response: handle-interruption-graceful-shutdown-completed

This file captures what a generic assistant produces WITHOUT the
ec2-spot-interruption-operator skill loaded.

---

Your Spot Instance i-0abc123def456 received an interruption warning. The
instance will be terminated in 2 minutes. The replacement should launch
automatically via the Spot Fleet.

You can check the replacement status with:

```bash
aws ec2 describe-spot-fleet-instances --spot-fleet-request-id sfr-prod-web
```

If you have a Lambda function for graceful shutdown, it should handle
deregistering the instance from the load balancer. Otherwise, you can
manually deregister it:

```bash
aws elbv2 deregister-targets \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/prod-web-tg/... \
  --targets Id=i-0abc123def456
```
