# Baseline (no-skill) — fargate-no-nat-gateway

> This is the response a model produces **without** the skill definition.
> It deploys the service without flagging that private subnets without
> NAT Gateway or VPC endpoints will cause the task to fail at image pull
> (ECR endpoint unreachable) and at runtime (DynamoDB API unreachable).

---

```bash
aws ecs create-service \
  --cluster workers-prod \
  --service-name report-worker-prod \
  --task-definition report-worker \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-priv-a,subnet-priv-b]}"
```

Make sure the task role has DynamoDB permissions. The execution
role needs AmazonECSTaskExecutionRolePolicy.
