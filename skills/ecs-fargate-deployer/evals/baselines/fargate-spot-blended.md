# Baseline (no-skill) — fargate-spot-blended

> This is the response a model produces **without** the skill definition.
> It uses the legacy launch-type=FARGATE API instead of a capacity-provider
> strategy, missing the Fargate Spot blend entirely (Spot is not a launch
> type). It also misses the circuit breaker, the Secrets Manager
> permission, and the pre-created log group.

---

```bash
aws ecs create-service \
  --cluster workers-prod \
  --service-name email-worker-prod \
  --task-definition email-worker \
  --desired-count 6 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-priv-a,subnet-priv-b],securityGroups=[sg-email-worker]}"
```

For Fargate Spot, you can set the launch type to FARGATE_SPOT if
you want to save cost. Use the AWS console to switch.

Set up CloudWatch Logs in the container definition with the
awslogs driver.
