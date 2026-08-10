# Baseline (no-skill) — public-api-alb-autoscale

> This is the response a model produces **without** the skill definition.
> It produces a basic create-service command but misses the target_type=ip
> requirement on the ALB target group, the separate execution role and
> task role (often conflated), the Secrets Manager permission on the
> execution role, the deployment circuit breaker configuration, the
> pre-created CloudWatch log group with retention, the container health
> check (so the circuit breaker has no signal), and the structured
> checklist.

---

Here's how to deploy your ECS Fargate service:

```bash
aws ecs create-service \
  --cluster payments-prod \
  --service-name payments-api-prod \
  --task-definition payments-api \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-aaa,subnet-bbb],securityGroups=[sg-payments-api]}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-payments-api/abc,containerName=app,containerPort=8080"
```

Make sure your task definition has the right CPU and memory for
Fargate. Use 0.5 vCPU and 1 GB for this API.

For the DB password, you can put it as an environment variable in
the task definition.

If you want auto-scaling, set up a target tracking policy on CPU
after the service is created.
