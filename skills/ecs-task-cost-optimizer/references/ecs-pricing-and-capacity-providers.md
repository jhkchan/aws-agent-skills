# ECS Pricing and Capacity Providers Reference

Supplementary reference for the ECS Task Cost Optimizer skill. Loaded
on-demand when detailed pricing math, Fargate valid combinations,
Graviton2 compatibility matrices, capacity provider configuration, or
Savings Plan discount tiers are needed.

## Fargate pricing (us-east-1, 2026, USD)

### Per-second compute pricing

| Architecture | $/vCPU-hour | $/GB-hour | Notes |
|---|---|---|---|
| x86_64 | $0.04048 | $0.004445 | Baseline Fargate rate |
| arm64 (Graviton2) | $0.03238 | $0.003561 | ~20% cheaper than x86_64 |

### Billing rules

- Per-second billing with 1-minute minimum per task
- CPU and memory billed independently (not bundled)
- Fargate Spot: up to 70% discount, but reclaimable (2-min warning)
- No charge for ECS control plane (only for compute resources)

### Fargate Spot pricing

| Architecture | $/vCPU-hour | $/GB-hour | Discount vs on-demand |
|---|---|---|---|
| x86_64 Spot | $0.012244 | $0.001346 | ~70% off |
| arm64 Spot | $0.009779 | $0.001079 | ~70% off |

### Free tier

- No free tier for Fargate compute
- ECS control plane is always free (no per-cluster charge)

## EC2-backed ECS pricing

EC2-backed ECS charges for the underlying EC2 instances only. The ECS
surcharge is $0.00 — you pay for instances regardless of how many tasks
run on them.

### Common ECS instance types (us-east-1, 2026)

| Instance type | vCPU | Memory | $/hr (on-demand) | $/hr (spot) | Typical task density |
|---|---|---|---|---|---|
| t3.medium | 2 | 4 GB | $0.0416 | $0.0125 | 2-4 small tasks |
| t3.large | 2 | 8 GB | $0.0832 | $0.0250 | 3-5 medium tasks |
| m5.large | 2 | 8 GB | $0.096 | $0.029 | 3-5 medium tasks |
| m5.xlarge | 4 | 16 GB | $0.192 | $0.058 | 6-10 tasks |
| m5.2xlarge | 8 | 32 GB | $0.384 | $0.115 | 10-15 tasks |
| m5.4xlarge | 16 | 64 GB | $0.768 | $0.230 | 15-25 tasks |
| c5.large | 2 | 4 GB | $0.085 | $0.026 | CPU-bound tasks |
| c5.xlarge | 4 | 8 GB | $0.170 | $0.051 | CPU-bound tasks |
| r5.large | 2 | 16 GB | $0.126 | $0.038 | Memory-bound tasks |

### Graviton instance types (arm64)

| Instance type | vCPU | Memory | $/hr (on-demand) | $/hr (spot) | Savings vs x86 |
|---|---|---|---|---|---|
| c7g.large | 2 | 4 GB | $0.0735 | $0.0221 | ~14% cheaper |
| m7g.large | 2 | 8 GB | $0.0836 | $0.0251 | ~13% cheaper |
| r7g.large | 2 | 16 GB | $0.1097 | $0.0330 | ~13% cheaper |
| c7g.xlarge | 4 | 8 GB | $0.1470 | $0.0442 | ~14% cheaper |
| m7g.xlarge | 4 | 16 GB | $0.1672 | $0.0502 | ~13% cheaper |
| r7g.xlarge | 4 | 32 GB | $0.2194 | $0.0660 | ~13% cheaper |

### Fargate-EC2 crossover analysis

| Task count | Fargate cost (1 vCPU/2 GB each) | EC2 cost (m5.large × needed) | Winner |
|---|---|---|---|
| 2 tasks | $72.08/mo | $70.08 (1 × m5.large) | EC2 (marginal) |
| 5 tasks | $180.20/mo | $210.24 (3 × m5.large) | Fargate |
| 8 tasks | $288.32/mo | $210.24 (3 × m5.large) | EC2 (27% cheaper) |
| 12 tasks | $432.48/mo | $280.32 (4 × m5.large) | EC2 (35% cheaper) |
| 20 tasks | $720.80/mo | $420.48 (6 × m5.large) | EC2 (42% cheaper) |
| 50 tasks | $1,802.00/mo | $840.96 (12 × m5.large) | EC2 (53% cheaper) |

**Crossover rule:** for always-on workloads with >5-8 tasks of 1 vCPU
each, EC2 is consistently cheaper. Below that, Fargate's simplicity
outweighs the marginal cost difference.

## Fargate valid CPU/memory combinations

Fargate enforces specific CPU-to-memory combinations. Not all
combinations are valid.

| CPU (vCPU) | CPU value | Valid memory (GB) |
|---|---|---|
| 0.25 | 256 | 0.5, 1, 2 |
| 0.5 | 512 | 1, 2, 3, 4 |
| 1 | 1024 | 2, 3, 4, 5, 6, 7, 8 |
| 2 | 2048 | 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 |
| 4 | 4096 | 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, ..., 30 |
| 8 | 8192 | 16, 17, 18, ..., 60 |
| 16 | 16384 | 32, 33, 34, ..., 120 |

Note: the `cpu` field in the task definition uses the vCPU × 1024
convention (e.g., 0.5 vCPU = 512). The `memory` field uses MB (e.g.,
1024 MB = 1 GB).

## Graviton2 (arm64) compatibility matrix

| Runtime | ARM64 support | Migration risk | Notes |
|---|---|---|---|
| Node.js 18/20/22 | Full | LOW | Pure JS apps; verify native addons (node-gyp) |
| Python 3.9/3.11/3.12 | Full | LOW | Verify C-extension deps have aarch64 wheels |
| Java 11/17/21 (Corretto) | Full | LOW-MEDIUM | Verify JNI/native libs; test GC behavior |
| .NET 6/8 | Full | MEDIUM | Verify native interop libraries |
| Go 1.21+ | Full | LOW | Recompile with `GOARCH=arm64 GOOS=linux` |
| Ruby 3.2/3.3 | Full | LOW | Verify native gem extensions |
| provided.al2023 (custom) | Full | MEDIUM | Recompile custom runtime for aarch64 |
| Rust 1.70+ | Full | LOW | Recompile with `--target aarch64-unknown-linux-gnu` |
| C/C++ | Conditional | MEDIUM-HIGH | Recompile; verify inline assembly, SSE intrinsics |

### Container image architecture check

```bash
# Check if a container image is multi-arch or arm64-native
docker manifest inspect <image>:<tag> | jq '.manifests[].platform.architecture'

# For multi-arch builds:
docker buildx build --platform linux/amd64,linux/arm64 -t <image>:<tag> --push .
```

## Capacity provider configuration

### EC2-backed capacity provider with managed scaling

```bash
# Create an ASG for the capacity provider
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name ecs-prod-asg \
  --launch-template LaunchTemplateId=<lt-id> \
  --min-size 2 --max-size 10 --desired-capacity 3 \
  --vpc-zone-identifier "subnet-xxx,subnet-yyy"

# Create the capacity provider
aws ecs create-capacity-provider \
  --name ec2-on-demand-provider \
  --auto-scaling-group-provider \
    autoScalingGroupArn=arn:aws:autoscaling:...:ecs-prod-asg,\
    managedScaling=status=ENABLED,targetCapacity=80,\
    managedTerminationProtection=ENABLED

# Assign to cluster with strategy
aws ecs put-cluster-capacity-providers \
  --cluster prod-cluster \
  --capacity-providers ec2-on-demand-provider \
  --default-capacity-provider-strategy \
    capacityProvider=ec2-on-demand-provider,weight=1,base=2
```

### Spot + on-demand capacity provider strategy

```bash
# Two capacity providers: spot (70% weight) + on-demand (30% weight, base=2)
aws ecs put-cluster-capacity-providers \
  --cluster prod-cluster \
  --capacity-providers spot-provider on-demand-provider \
  --default-capacity-provider-strategy \
    capacityProvider=spot-provider,weight=7,\
    capacityProvider=on-demand-provider,weight=3,base=2
```

| Parameter | Effect |
|---|---|
| `base` | Minimum tasks on this provider before applying weights |
| `weight` | Relative proportion of tasks on this provider after base is met |
| `managedScaling.targetCapacity` | Target instance utilization (0-100%) |
| `managedTerminationProtection` | Prevents ASG from terminating instances with running tasks |

### Fargate capacity providers

Fargate has two built-in capacity providers:
- `FARGATE` — on-demand Fargate
- `FARGATE_SPOT` — spot Fargate (up to 70% discount, reclaimable)

```bash
aws ecs put-cluster-capacity-providers \
  --cluster prod-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE_SPOT,weight=7,\
    capacityProvider=FARGATE,weight=3,base=1
```

## Savings Plan discount tiers

### Compute Savings Plans (apply to Fargate + EC2 + Lambda)

| Commitment | Discount vs on-demand | Upfront vs no-upfront |
|---|---|---|
| 1-year, no upfront | ~30-40% | No upfront payment |
| 1-year, partial upfront | ~40-48% | Partial upfront |
| 1-year, all upfront | ~50-54% | Full upfront |
| 3-year, no upfront | ~45-55% | No upfront payment |
| 3-year, partial upfront | ~55-62% | Partial upfront |
| 3-year, all upfront | ~60-72% | Full upfront |

### What Compute SPs cover

- Fargate vCPU-hours and GB-hours
- EC2 instance-hours (any family, any size, any AZ)
- Lambda compute (GB-seconds + requests)

### What Compute SPs do NOT cover

- EBS volumes
- EFS storage
- NAT Gateway
- Application Load Balancer
- Data transfer

### SP coverage analysis commands

```bash
# Check SP coverage for ECS/Fargate spend
aws savingsplans describe-savings-plans-coverage \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"Service","Values":["Amazon Elastic Container Service","AmazonEC2","AWS Fargate"]}}'

# Check SP utilization
aws savingsplans describe-savings-plans-utilization \
  --time-period Start=2026-07-01,End=2026-07-31
```

## Regional pricing multipliers

Approximate multiplier vs us-east-1 for Fargate and EC2.

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| us-west-1 | 1.05x | Slight premium |
| eu-west-1, eu-west-2, eu-central-1 | 1.10-1.15x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10-1.15x | |
| ap-south-1 (Mumbai) | 1.15-1.25x | |
| sa-east-1 (São Paulo) | 1.35-1.50x | Highest premium |
| af-south-1 (Cape Town) | 1.30-1.45x | |

Always re-check via the AWS Pricing API for production estimates.

## Extended NEVER list (supplementary anti-patterns)

- NEVER recommend EC2-backed ECS for a team that has no EC2 operational
  experience. The cost saving is real but the operational burden (AMI
  patching, ASG management, capacity provider tuning) can exceed the
  saving in engineering time.

- NEVER recommend spot capacity for tasks with `essential` containers
  that do not handle SIGTERM. The 2-minute warning requires application
  cooperation; ignoring SIGTERM causes data loss.

- NEVER recommend a 3-year Savings Plan for a workload that may migrate
  to a different service (e.g., ECS to Lambda, or self-managed to
  managed). The commitment is locked in regardless of architecture change.

- NEVER assume Container Insights is enabled. It is opt-in. Before
  recommending right-sizing, verify metrics exist; if absent, enable it
  and wait 14 days.

- NEVER recommend right-sizing below the Fargate minimum valid
  combination. 0.25 vCPU requires 0.5-2 GB memory; 0.5 vCPU requires
  1-4 GB. Verify the combination is valid.

- NEVER recommend `binpack` placement for tasks that require fault
  isolation. Binpack maximizes density but concentrates blast radius
  if an instance fails.

- NEVER recommend Fargate Spot for services with SLA requirements that
  cannot tolerate 2-minute interruption notices. Spot reclamation is
  guaranteed to happen — it is a question of when, not if.

- NEVER increase auto-scaling `MaxCapacity` without verifying the
  underlying capacity provider can provision the additional instances.
  Fargate scales transparently; EC2-backed scaling is limited by ASG max.

- NEVER recommend task definition memory reduction without monitoring
  for OOM kills for at least 48 hours post-change. Memory is not
  compressible — the failure mode is immediate and silent (container
  killed, not degraded).

- NEVER batch-update more than 5 services in a single output block.

---

## Step 1 — Fargate vs EC2 crossover math (moved from SKILL.md)

**The crossover math (~30% utilization rule):**
```
Fargate cost (per task, per hour):
  vCPU: 1.0 × $0.04048 = $0.04048/hr
  Memory: 2 GB × $0.004445 = $0.00889/hr
  Total: $0.04937/hr → $36.04/month per task

EC2 cost (per instance, per hour, amortized across tasks):
  m5.large (2 vCPU, 8 GB): $0.096/hr → $70.08/month
  If 4 tasks pack onto 1 instance: $17.52/task/month
  Saving vs Fargate: 51% for the same task footprint

Crossover: if average tasks per instance > 2-3 (steady), EC2 wins.
If tasks are bursty or < 30% utilization, Fargate's per-second wins.
```

---

## Step 2 — Fargate arm64 pricing comparison (moved from SKILL.md)

**Fargate pricing comparison (us-east-1, 2026):**
```
x86_64:  $0.04048/vCPU-hr + $0.004445/GB-hr
arm64:   $0.03238/vCPU-hr + $0.003561/GB-hr  (20% cheaper)
```

---

## Step 2 — ARM64 compatibility check table (moved from SKILL.md)

**Compatibility check before migration:**

| Application type | ARM64 risk | Verification step |
|---|---|---|
| Interpreted (Python, Node, Ruby) | LOW | Verify native deps have arm64 wheels/gems |
| JVM (Java, Kotlin, Scala) | LOW | Verify JNI libs; JDK 11+ supports arm64 |
| .NET | LOW-MEDIUM | Verify native interop libs |
| Go | LOW | Recompile with `GOARCH=arm64` |
| Rust | LOW | Recompile with `--target aarch64-unknown-linux-gnu` |
| C/C++ | MEDIUM | Recompile for arm64; verify inline assembly |
| Container with x86 binary | HIGH | Requires multi-arch build (`docker buildx`) |

---

## Step 3 — right-sizing math and valid CPU/memory combinations (moved from SKILL.md)

**Right-sizing math (Fargate, 8 tasks):**
```
Current: 1 vCPU, 2 GB per task → $0.04937/hr × 8 tasks × 730 hr = $288.36/month
Proposed: 0.5 vCPU, 1 GB per task → $0.02473/hr × 8 tasks × 730 hr = $144.45/month
Saving: $143.91/month (50%) — if utilization was < 20% at the original size
```

**Fargate valid CPU/memory combinations:**

| CPU (vCPU) | Memory range (GB) |
|---|---|
| 0.25 | 0.5, 1, 2 |
| 0.5 | 1, 2, 3, 4 |
| 1 | 2, 3, 4, 5, 6, 7, 8 |
| 2 | 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 |
| 4 | 8, 9, 10, ..., 30 |
| 8 | 16, 17, ..., 60 |

---

## Step 5 — Savings Plan vs Reserved Instance (moved from SKILL.md)

**Savings Plan vs Reserved Instance:**

| Feature | Compute SP | Reserved Instance |
|---|---|---|
| Applies to Fargate | YES | NO |
| Applies to EC2 ECS | YES | YES |
| Flexibility (any instance family) | YES (any family, any size, any AZ) | NO (specific family only) |
| Applies to Lambda | YES | NO |
| Discount depth | Up to 54% (1yr), 72% (3yr) | Up to 72% (3yr Standard) |

---

## Step 8 — impact estimation formula (moved from SKILL.md)

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (Fargate) vCPU_hours × $0.04048 + GB_hours × $0.004445
  OR
  (EC2) instance_count × instance_hourly × 730

projected_monthly_cost =
  (Fargate arm64) vCPU_hours × $0.03238 + GB_hours × $0.003561
  OR
  (EC2 Graviton) instance_count × graviton_hourly × 730
  OR
  (right-sized) reduced_vCPU_hours × rate + reduced_GB_hours × rate
  × (1 - SP_discount) if Savings Plan applied

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: launch type, architecture, task count,
utilization baseline, pricing region, capacity provider mix.
