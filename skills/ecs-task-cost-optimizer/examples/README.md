# Example usage: ecs-task-cost-optimizer

A walkthrough showing the skill optimizing an over-provisioned Fargate
service running on x86_64, demonstrating the right-sizing analysis from
Container Insights, the Graviton2 (arm64) architecture migration, the
dollar savings math, and the canary deployment workflow.

## Input (user prompt)

> We're doing a container cost audit. This Fargate service is running
> 8 tasks at 1 vCPU / 2 GB each and only using 12% CPU. Help me
> optimize the cost.

```text
ServiceName: order-api-prod
Cluster: prod-cluster
LaunchType: FARGATE
TaskDefinition: order-api:42
CPU: 1024 (1 vCPU)
Memory: 2048 MB
Architecture: x86_64
Region: us-east-1
DesiredCount: 8
Capacity provider: FARGATE (on-demand)

Metrics (last 30 days, Container Insights):
  - CPUUtilization avg: 12%, p95: 25%
  - MemoryUtilization avg: 18%, p95: 30%
  - RunningTaskCount avg: 8

Workload context: Node.js 20 REST API. Pure JavaScript with no native
C/C++ dependencies (no node-gyp, no ffi-napi). Container image uses
node:20-alpine base. All npm packages are pure JS. SQS-triggered data
enrichment — no compliance or latency constraints requiring headroom.

Cost Explorer (last month):
  - Fargate compute: $288.32/month
```

## Skill output

```text
TARGET: order-api-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Fargate service at 1.0 vCPU / 2.0 GB with avg CPUUtilization
  12% and MemoryUtilization 18% across 8 tasks. Two findings: (1)
  right-size to 0.5 vCPU / 1.0 GB (Container Insights confirms steady
  p95 utilization under 30% of allocated); (2) migrate from x86_64 to
  arm64 (Node.js 20 — full arm64 support, no native deps). Combined
  monthly saving: $172.97 (60% compute reduction).
RECOMMENDATION:
  Current: FARGATE, 1.0 vCPU, 2.0 GB, x86_64, 8 tasks, on-demand
  Proposed: FARGATE, 0.5 vCPU, 1.0 GB, arm64, 8 tasks, on-demand
  Dimensions changed: right-size (Step 3) + architecture (Step 2)
  Dimensions checked: launch-type ✓ (Fargate, < 30% utilization confirms Fargate)
    architecture → (x86 to arm64)  right-size → (1.0/2.0 to 0.5/1.0)
    spot ✓ (Fargate, no spot)  savings-plan ✓ (evaluate post-change)
    placement ✓ (Fargate)  autoscaling ✓ (target tracking at 60%)
  Confidence: HIGH — Container Insights confirms 30-day avg CPUUtilization
    12% and MemoryUtilization 18%; Node.js 20 fully supports arm64;
    no native dependencies in container image.
ESTIMATED_SAVINGS:
  Current monthly: $288.32
    compute: 1.0 vCPU × 8 tasks × 730 hr × $0.04048 = $236.40
    memory: 2.0 GB × 8 tasks × 730 hr × $0.004445 = $51.92
  Projected monthly: $115.35
    compute: 0.5 vCPU × 8 tasks × 730 hr × $0.03238 = $94.55
    memory: 1.0 GB × 8 tasks × 730 hr × $0.003561 = $20.80
  Monthly saving: $172.97 ($288.32 − $115.35)
  Annual saving: $2,075.64
MIGRATION_STEPS:
  1. Verify container image is arm64 or multi-arch:
     docker manifest inspect <image>:latest | jq '.manifests[].platform.architecture'
  2. If not multi-arch, rebuild:
     docker buildx build --platform linux/amd64,linux/arm64 -t <image>:latest --push .
  3. Register new task definition with arm64 + right-sized resources:
     aws ecs register-task-definition --family order-api
       --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX
       --cpu 512 --memory 1024 --container-definitions file://containers-arm64.json
  4. Deploy via canary (10% → 50% → 100%):
     aws ecs update-service --cluster prod-cluster
       --service order-api-prod --task-definition order-api:43
  5. Monitor CPUUtilization and MemoryUtilization for 7 days post-change.
  6. If OOM events appear, roll back to prior revision immediately.
CONFIRM: About to update-service on order-api-prod
  (1.0 vCPU x86 → 0.5 vCPU arm64, 2.0 GB → 1.0 GB). Monthly saving
  $172.97 (60.0%). Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **Right-sizing and architecture migration stack.** A generic assistant
   catches the right-sizing (12% utilization is obviously over-provisioned)
   but misses that arm64 migration stacks 20% on top. The skill identifies
   both dimensions and compounds the savings.

2. **Fargate arm64 pricing is different from x86.** A generic assistant may
   say "switch to arm64" without citing the specific pricing delta ($0.03238
   vs $0.04048 per vCPU-hour). The skill shows the exact formula so the
   operator can verify.

3. **Container image architecture verification.** A generic assistant
   recommends arm64 without checking whether the container image supports
   it. The skill includes `docker manifest inspect` as the first migration
   step and a multi-arch rebuild fallback.

4. **Canary deployment workflow.** A generic assistant goes straight to
   `update-service`. The skill specifies a canary deployment (10% → 50% →
   100%) because both CPU reduction and architecture change introduce risk
   (OOM on memory reduction, runtime incompatibility on arm64).

5. **OOM risk on memory reduction.** A generic assistant reduces memory
   without warning. The skill explicitly flags that memory is not
   compressible — an OOM kill is the failure mode — and includes a rollback
   step in MIGRATION_STEPS.

6. **Full seven-dimension coverage.** The skill checks launch-type,
   architecture, right-size, spot, savings-plan, placement, and autoscaling
   — confirming each has no additional finding. A generic assistant focuses
   only on the obvious CPU over-provisioning.

7. **Dollar arithmetic is shown explicitly.** The skill shows the formula
   (`0.5 × 8 × 730 × $0.03238 = $94.55`) so the operator can verify. A
   generic assistant says "this should save money" without showing the math.

## Slash-command invocation

```
/aws:optimize-ecs-task-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our ECS task spend for the container cost audit"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: ecs-task-cost-optimizer]` and hands
off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm the new task definition landed
aws ecs describe-services --cluster prod-cluster \
  --services order-api-prod \
  --query 'services[0].taskDefinition' --output text

# Confirm the runtime platform is arm64
aws ecs describe-task-definition --task-definition order-api:43 \
  --query 'taskDefinition.runtimePlatform' --output json

# Monitor CPU and memory for 7 days post-change
aws cloudwatch get-metric-statistics --namespace ECS/ContainerInsights \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=prod-cluster Name=ServiceName,Value=order-api-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

aws cloudwatch get-metric-statistics --namespace ECS/ContainerInsights \
  --metric-name MemoryUtilization \
  --dimensions Name=ClusterName,Value=prod-cluster Name=ServiceName,Value=order-api-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json
```

If MemoryUtilization exceeds 80% or OOM events appear in Container
Insights, roll back immediately:

```bash
aws ecs update-service --cluster prod-cluster \
  --service order-api-prod --task-definition order-api:42
```

## Fleet-wide extension

For a cluster with many ECS services, run the skill in batch mode:

1. List all services:
   ```bash
   aws ecs list-services --cluster prod-cluster --output json | \
     jq '.serviceArns[]' | jq -s '.'
   ```
2. Filter to services with RunningTaskCount > 1 (cost relevance).
3. Pull Container Insights CPU and memory utilization for each (14-30 day window).
4. Sort by monthly Fargate/EC2 cost (largest first).
5. Slice into batches of 5 services.
6. For each batch: emit per-service MIGRATION_STEPS, then a single
   CONFIRM for the batch.
7. Verify each batch before proceeding to the next.
8. After the right-sizing sweep, evaluate Graviton2 (arm64) migration
   eligibility for remaining x86 services.
9. After architecture sweep, evaluate spot capacity provider eligibility
   for EC2-backed stateless services.
10. Finally, evaluate Savings Plan purchase for stabilized spend.
