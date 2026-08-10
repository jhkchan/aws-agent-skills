# Baseline (no-skill) — wrong-target-type-instance

> This is the response a model produces **without** the skill definition.
> It accepts the target_type=instance without flagging the incompatibility
> with Fargate, missing the silent failure mode (target registration
> never succeeds for Fargate tasks on an instance-type target group).

---

Here's the deployment command:

```bash
aws ecs create-service \
  --cluster apps-prod \
  --service-name internal-api-prod \
  --task-definition internal-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-priv-a,subnet-priv-b],securityGroups=[sg-internal-api]}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-internal-api/abc,containerName=app,containerPort=3000"
```

Make sure the task size matches a Fargate-supported combo (0.25
vCPU with 512 MB is valid).
