# Baseline (no-skill) response: graviton2-migration

This file captures what a generic assistant produces WITHOUT the
ecs-task-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, ARM64 compatibility
verification, arm64 pricing math, CONFIRM gate, canary deploy).

---

Your ECS service is running on x86_64 Fargate with 8 tasks. Since it's
a Node.js application with no native dependencies, you can switch to
Graviton2 (arm64) which is about 20% cheaper on Fargate.

You'll need to register a new task definition with arm64 runtime
platform:

```
aws ecs register-task-definition --family order-api --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX ...
```

Then update the service to use the new revision. With 8 tasks at 0.5
vCPU and 1 GB, you'd save about $29/month.

Make sure your container image works on arm64. Since you're using
node:20-alpine, it should be fine, but test it first.
