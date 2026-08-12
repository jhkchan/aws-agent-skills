# Worked Examples — ECS Task Cost Optimizer

Full worked examples covering Fargate-to-EC2 crossover, Graviton2
migration, task right-sizing, spot capacity provider migration,
already-optimized services, NEED_MORE_INFO, and an end-to-end
optimisation walkthrough. Loaded on demand — kept out of the main
SKILL.md body so the procedure stays scannable.

## Worked example — Fargate to EC2 crossover

```text
TARGET: web-api-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Always-on Fargate service with 20 tasks at 1 vCPU / 2 GB each,
  steady CPUUtilization 65% and MemoryUtilization 58%. Past the 30%
  crossover — EC2 backing with binpack placement packs 4 tasks per
  m5.large, needing 5 instances. EC2 cost: $350.40/month vs Fargate
  $720.80/month — 51% saving. Team confirmed willingness to manage EC2.
RECOMMENDATION:
  Current: FARGATE, 1.0 vCPU, 2.0 GB, x86_64, 20 tasks, on-demand
  Proposed: EC2 (5x m5.large), 1.0 vCPU, 2.0 GB, x86_64, 20 tasks, on-demand + binpack
  Dimensions changed: launch-type (Step 1) + placement (Step 6)
  Dimensions checked: launch-type → (Fargate to EC2)  architecture ✓ (x86, no arm64 dep)
    right-size ✓ (CPU/mem at 65%/58% — well-provisioned)  spot ✓ (no, stateful)
    savings-plan ✓ (none yet, evaluate post-migration)  placement → (spread to binpack)
    autoscaling ✓ (target tracking at 60% CPU)
  Confidence: HIGH — Container Insights confirms 30-day steady utilization
    > 30%; Cost Explorer confirms $720.80/month Fargate; team confirmed EC2 capability.
ESTIMATED_SAVINGS:
  Current monthly: $720.80
    compute: 1.0 vCPU × 20 tasks × 730 hr × $0.04048 = $590.98
    memory: 2.0 GB × 20 tasks × 730 hr × $0.004445 = $129.82
  Projected monthly: $350.40
    ec2: 5 × m5.large × $0.096/hr × 730 hr = $350.40
    (ecs surcharge: $0.00)
  Monthly saving: $370.40 ($720.80 − $350.40)
  Annual saving: $4,444.80
MIGRATION_STEPS:
  1. Create EC2 ASG for ECS capacity provider:
     aws autoscaling create-auto-scaling-group
       --auto-scaling-group-name ecs-web-api-asg
       --launch-template LaunchTemplateId=<lt-id>
       --min-size 3 --max-size 8 --desired-capacity 5
       --vpc-zone-identifier "subnet-xxx,subnet-yyy"
  2. Create capacity provider:
     aws ecs create-capacity-provider --name ec2-web-provider
       --auto-scaling-group-provider autoScalingGroupArn=<asg-arn>,managedScaling=...
  3. Update cluster capacity providers:
     aws ecs put-cluster-capacity-providers --cluster prod-cluster
       --capacity-providers ec2-web-provider
       --default-capacity-provider-strategy capacityProvider=ec2-web-provider,weight=1,base=2
  4. Update service to use EC2 launch + binpack placement:
     aws ecs update-service --cluster prod-cluster
       --service web-api-prod --capacity-provider-strategy ...
  5. Monitor for task migration completion and instance utilization for 7 days.
CONFIRM: About to migrate web-api-prod from Fargate to EC2-backed (5x m5.large).
  Saving $370.40/month (51%). Requires ongoing EC2 management (ASG, AMI patching).
  Proceed? (yes/no)
```

## Worked example — Graviton2 (arm64) migration

```text
TARGET: order-api-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Fargate service on x86_64 running Node.js 20 with no native deps.
  Migrating to arm64 yields 20% compute discount. Container Insights
  confirms utilization is healthy (35% CPU, 40% memory) — no right-sizing
  needed. arm64 pricing applies automatically via runtimePlatform.
RECOMMENDATION:
  Current: FARGATE, 0.5 vCPU, 1.0 GB, x86_64, 8 tasks, on-demand
  Proposed: FARGATE, 0.5 vCPU, 1.0 GB, arm64, 8 tasks, on-demand
  Dimensions changed: architecture (Step 2)
  Dimensions checked: launch-type ✓ (Fargate, < 30% utilization is not met at 35%)
    architecture → (x86 to arm64)  right-size ✓ (35%/40% utilization is healthy)
    spot ✓ (Fargate, no spot)  savings-plan ✓ (none, but spend low)
    placement ✓ (Fargate)  autoscaling ✓ (target tracking at 60%)
  Confidence: HIGH — Container Insights confirms healthy utilization;
    Node.js 20 fully supports arm64; all npm packages are pure JS
    (verified: no node-gyp, no ffi-napi, no native addons).
ESTIMATED_SAVINGS:
  Current monthly: $144.44
    compute: 0.5 vCPU × 8 tasks × 730 hr × $0.04048 = $118.20
    memory: 1.0 GB × 8 tasks × 730 hr × $0.004445 = $25.97
  Projected monthly: $115.31
    compute: 0.5 vCPU × 8 tasks × 730 hr × $0.03238 = $94.55
    memory: 1.0 GB × 8 tasks × 730 hr × $0.003561 = $20.80
  Monthly saving: $29.13 ($144.44 − $115.31)
  Annual saving: $349.56
MIGRATION_STEPS:
  1. Verify container image is arm64 or multi-arch:
     docker manifest inspect <image>:latest | jq '.manifests[].platform.architecture'
  2. If not multi-arch, rebuild:
     docker buildx build --platform linux/amd64,linux/arm64 -t <image>:latest --push .
  3. Register new task definition with arm64:
     aws ecs register-task-definition --family order-api
       --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX
       --cpu 512 --memory 1024 --container-definitions file://containers.json
  4. Deploy via canary (10% → 50% → 100%):
     aws ecs update-service --cluster prod-cluster
       --service order-api-prod --task-definition order-api:43
  5. Monitor CPUUtilization and error rate for 7 days.
CONFIRM: About to migrate order-api-prod from x86_64 to arm64 on Fargate.
  Saving $29.13/month (20%). Requires arm64 container image verification.
  Proceed? (yes/no)
```

## Worked example — task right-sizing

```text
TARGET: data-processor-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Fargate service at 1 vCPU / 2 GB with avg CPUUtilization 12%
  and MemoryUtilization 18% across 8 tasks. Significantly over-provisioned.
  Right-sizing to 0.5 vCPU / 1.0 GB (p95 CPU 25% × 2 safety = 50% headroom,
  p95 memory 30% × 1.5 safety = 45% → fits 1 GB). Saves 50% on compute.
RECOMMENDATION:
  Current: FARGATE, 1.0 vCPU, 2.0 GB, x86_64, 8 tasks, on-demand
  Proposed: FARGATE, 0.5 vCPU, 1.0 GB, x86_64, 8 tasks, on-demand
  Dimensions changed: right-size (Step 3)
  Dimensions checked: launch-type ✓ (Fargate, < 30% utilization confirms Fargate)
    architecture ✓ (Python 3.12, arm64 eligible but not in scope)
    right-size → (1.0/2.0 to 0.5/1.0)  spot ✓ (Fargate)
    savings-plan ✓ (none, evaluate post-right-size)  placement ✓ (Fargate)
    autoscaling ✓ (target tracking)
  Confidence: HIGH — Container Insights confirms 30-day avg CPU 12%, memory 18%;
    p95 values (25%/30%) provide adequate headroom at the reduced allocation.
ESTIMATED_SAVINGS:
  Current monthly: $288.32
    compute: 1.0 vCPU × 8 tasks × 730 hr × $0.04048 = $236.40
    memory: 2.0 GB × 8 tasks × 730 hr × $0.004445 = $51.92
  Projected monthly: $144.44
    compute: 0.5 vCPU × 8 tasks × 730 hr × $0.04048 = $118.20
    memory: 1.0 GB × 8 tasks × 730 hr × $0.004445 = $25.97
  Monthly saving: $143.88 ($288.32 − $144.44)
  Annual saving: $1,726.56
MIGRATION_STEPS:
  1. Register new task definition with reduced resources:
     aws ecs register-task-definition --family data-processor
       --cpu 512 --memory 1024 --container-definitions file://containers.json
  2. Deploy via canary (10% → 50% → 100%):
     aws ecs update-service --cluster prod-cluster
       --service data-processor-prod --task-definition data-processor:8
  3. Monitor CPUUtilization and MemoryUtilization for 48 hours.
  4. If MemoryUtilization exceeds 80% or OOM events appear, roll back
     to the prior task definition immediately.
CONFIRM: About to right-size data-processor-prod (1.0/2.0 to 0.5/1.0).
  Saving $143.88/month (50%). Monitor for OOM — memory is not compressible.
  Proceed? (yes/no)
```

## Worked example — spot capacity provider migration

```text
TARGET: frontend-web-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: EC2-backed ECS service on 100% on-demand capacity. Stateless
  React SSR frontend with Redis-backed sessions — can tolerate spot
  interruption. Adding a spot capacity provider (70% spot + 30% on-demand
  base) reduces effective instance cost by ~50%.
RECOMMENDATION:
  Current: EC2 (4x m5.large), 100% on-demand, spread placement
  Proposed: EC2 (4x m5.large equivalent), spot 70% + on-demand 30%, binpack placement
  Dimensions changed: spot (Step 4) + placement (Step 6)
  Dimensions checked: launch-type ✓ (EC2, already optimal for always-on)
    architecture ✓ (x86, arm64 not in scope)  right-size ✓ (45%/50% utilization healthy)
    spot → (add spot capacity provider)  savings-plan ✓ (evaluate post-spot)
    placement → (spread to binpack)  autoscaling ✓ (target tracking at 60%)
  Confidence: HIGH — workload is stateless (Redis sessions); SIGTERM handler
    confirmed; stopTimeout=30s configured; ALB health checks enable draining.
ESTIMATED_SAVINGS:
  Current monthly: $280.32
    ec2: 4 × m5.large × $0.096/hr × 730 hr = $280.32
  Projected monthly: $160.08
    spot portion: ~3 instances × $0.029/hr × 730 = $63.51
    on-demand base: ~1 instance × $0.096/hr × 730 = $70.08
    binpack density gain: 1 fewer instance needed
    effective: $133.59 (recomputed: 3 spot + 1 on-demand = $133.59)
  Monthly saving: $146.73 ($280.32 − $133.59)
  Annual saving: $1,760.76
MIGRATION_STEPS:
  1. Create a spot-backed ASG:
     aws autoscaling create-auto-scaling-group
       --auto-scaling-group-name ecs-spot-asg
       --mixed-instances-policy ... (spot + on-demand mix)
  2. Create spot capacity provider:
     aws ecs create-capacity-provider --name spot-provider
       --auto-scaling-group-provider autoScalingGroupArn=<spot-asg-arn>,...
  3. Update cluster default strategy (spot 70% + on-demand 30% base=2):
     aws ecs put-cluster-capacity-providers --cluster prod-cluster
       --capacity-providers spot-provider on-demand-provider
       --default-capacity-provider-strategy
       capacityProvider=spot-provider,weight=7,
       capacityProvider=on-demand-provider,weight=3,base=2
  4. Update service placement to binpack:
     aws ecs update-service --cluster prod-cluster
       --service frontend-web-prod
       --placement-strategy type=binpack,field=memory
  5. Monitor for spot reclamation events and task drain/replacement for 7 days.
CONFIRM: About to add spot capacity provider (70% spot + 30% on-demand) and
  switch placement to binpack on frontend-web-prod. Saving $146.73/month (52%).
  Spot instances may be reclaimed with 2-min warning. Proceed? (yes/no)
```

## Worked example — already optimized

```text
TARGET: payment-api-prod
VERDICT: OPTIMIZED
REASON: Fargate service on arm64 (Node.js 20), right-sized at 0.5 vCPU /
  1 GB with healthy utilization (28% CPU, 40% memory). Covered by 1-year
  Compute SP at 52% discount (98% utilization). Capacity provider strategy:
  Fargate Spot 70% base + on-demand 30%. Auto-scaling at target tracking
  60% CPU. All seven optimization dimensions pass.
RECOMMENDATION:
  Current: FARGATE, 0.5 vCPU, 1.0 GB, arm64, 6 tasks, FARGATE_SPOT 70% + FARGATE 30%
  Dimensions checked: launch-type ✓ (Fargate Spot + on-demand)
    architecture ✓ (arm64, Graviton2)  right-size ✓ (28%/40% healthy)
    spot ✓ (Fargate Spot 70%)  savings-plan ✓ (1yr SP, 52% off, 98% utilized)
    placement ✓ (Fargate, auto)  autoscaling ✓ (target tracking 60%)
  Confidence: HIGH — all dimensions verified against describe-services,
    describe-task-definition, Container Insights, SP coverage, Cost Explorer.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Re-evaluate if traffic grows or at quarterly FinOps review.
```

## Worked example — NEED_MORE_INFO (Container Insights absent)

```text
TARGET: legacy-api-prod
VERDICT: NEED_MORE_INFO
REASON: CPUUtilization and MemoryUtilization metrics are absent for the
  requested 30-day window. Container Insights is not enabled on the
  cluster. Cannot make a right-sizing or optimization recommendation
  without utilization baseline data.
RECOMMENDATION:
  Current: FARGATE, 1.0 vCPU, 2.0 GB, x86_64, 4 tasks — pending data
  Proposed: pending data
  Confidence: LOW — no metrics to evaluate.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify without baseline)
MIGRATION_STEPS:
  1. Enable Container Insights on the cluster:
     aws ecs update-cluster-settings --cluster prod-cluster
       --settings name=containerInsights,value=enabled
  2. Wait 14-30 days for representative observation.
  3. Re-evaluate with CPUUtilization + MemoryUtilization data.
  4. Do NOT optimize based on assumed metrics.
```

## End-to-end optimisation walkthrough

This example walks through the complete workflow: analyse metrics,
identify waste via the decision tree, calculate savings, and provide
migration steps across multiple dimensions.

**Service profile:**
- Service: `order-api-prod`
- Launch type: FARGATE
- Task definition: `order-api:42` (1 vCPU, 2 GB, x86_64)
- Desired count: 8
- Region: us-east-1
- Container Insights: CPUUtilization avg 12%, p95 25%
- Container Insights: MemoryUtilization avg 18%, p95 30%
- No Savings Plan coverage
- No spot capacity provider
- Cost: $288.32/month

**Step 1 — Route through launch-type tree:**
- Always-on? YES. Steady utilization > 30%? NO (12% avg).
- Fargate confirmed. Per-second billing is correct for this load.

**Step 2 — Route through architecture tree:**
- Architecture: x86_64. Runtime: Node.js 20. Native deps: none.
- ARM64 eligible. 20% compute discount available.

**Step 3 — Route through right-sizing tree:**
- CPU avg 12% < 20% threshold AND allocated CPU (1024) > 256. Over-provisioned.
- Memory avg 18% < 30% threshold AND allocated memory (2048) > 512. Over-provisioned.
- Target: 0.5 vCPU (p95 CPU 25% × 2 = 50% headroom), 1.0 GB (p95 memory 30% × 1.5 = 45% of 1 GB).

**Step 4 — Calculate projected cost:**
```
Current (x86, 1.0/2.0):
  compute: 1.0 × 8 × 730 × $0.04048 = $236.40
  memory:  2.0 × 8 × 730 × $0.004445 = $51.92
  Total: $288.32/month

Projected (arm64, 0.5/1.0):
  compute: 0.5 × 8 × 730 × $0.03238 = $94.55
  memory:  1.0 × 8 × 730 × $0.003561 = $20.80
  Total: $115.35/month
```

**Step 5 — Savings summary:**
```
Monthly saving: $288.32 − $115.35 = $172.97 (60.0%)
Annual saving: $2,075.64
```

**Step 6 — Emit the output block:**
```text
TARGET: order-api-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Fargate service at 1.0 vCPU / 2.0 GB with avg CPUUtilization
  12% and MemoryUtilization 18% across 8 tasks. Two findings: (1)
  right-size to 0.5 vCPU / 1.0 GB; (2) migrate from x86_64 to arm64
  (Node.js 20, no native deps). Combined saving: 60% compute reduction.
RECOMMENDATION:
  Current: FARGATE, 1.0 vCPU, 2.0 GB, x86_64, 8 tasks, on-demand
  Proposed: FARGATE, 0.5 vCPU, 1.0 GB, arm64, 8 tasks, on-demand
  Dimensions changed: right-size (Step 3) + architecture (Step 2)
  Dimensions checked: launch-type ✓ (Fargate, < 30% utilization confirms Fargate)
    architecture → (x86 to arm64)  right-size → (1.0/2.0 to 0.5/1.0)
    spot ✓ (Fargate)  savings-plan ✓ (evaluate post-change)
    placement ✓ (Fargate)  autoscaling ✓ (target tracking at 60%)
  Confidence: HIGH — Container Insights confirms 30-day avg CPU 12%,
    memory 18%; Node.js 20 fully supports arm64; no native deps.
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
  2. Register new task definition with arm64 + right-sized resources:
     aws ecs register-task-definition --family order-api
       --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX
       --cpu 512 --memory 1024 --container-definitions file://containers-arm64.json
  3. Deploy via canary (10% → 50% → 100%):
     aws ecs update-service --cluster prod-cluster
       --service order-api-prod --task-definition order-api:43
  4. Monitor CPUUtilization and MemoryUtilization for 7 days post-change.
  5. If OOM events appear, roll back to prior revision immediately.
CONFIRM: About to update-service on order-api-prod
  (1.0 vCPU x86 → 0.5 vCPU arm64, 2.0 GB → 1.0 GB). Monthly saving
  $172.97 (60.0%). Proceed? (yes/no)
```
