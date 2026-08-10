# Baseline (no-skill) — ml-inference-arm64

> This is the response a model produces **without** the skill definition.
> It omits the runtimePlatform ARM64 configuration (so the task silently
> launches x86_64 and fails with exec format error on the arm64 image),
> misses the startPeriod grace window (so the slow-start ML container
> gets rolled back by the circuit breaker before model warmup), and uses
> awslogs instead of the requested FireLens log routing.

---

```bash
aws ecs create-service \
  --cluster ml-prod \
  --service-name image-tagger-prod \
  --task-definition image-tagger \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-priv-a,subnet-priv-b]}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/tg-image-tagger/abc,containerName=app,containerPort=8500"
```

For the container definition, use the standard awslogs driver
pointing at /ecs/image-tagger. Set the CPU and memory to 4096 /
16384 for ML workloads.

Auto-scale on CPU at 70% if you want.
