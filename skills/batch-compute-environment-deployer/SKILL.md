---
name: batch-compute-environment-deployer
description: 'Provisions AWS Batch compute environments, job queues, and job definitions with production defaults: EC2 vs Fargate vs EKS compute environment types, launch template integration, allocation strategy (BEST_FIT, BEST_FIT_PROGRESSIVE, SPOT_CAPACITY_OPTIMIZED), instance types and role, min/max/desired vCPUs, subnets and security groups, job queue with priority levels, job definition (container image, vCPU/memory, resources, env vars, mount points), job dependencies (sequential, N-ary), array jobs, CloudWatch metrics (CPUPct, MemoryPct, RUNNABLE), spot instance integration, Fargate platform version. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Batch compute environment, setting up a job queue, registering a job definition, configuring spot instances for Batch, or running array jobs with dependencies. Triggers: batch compute environment, job queue, job definition, allocation strategy, spot capacity, batch fargate, array jobs, job dependencies.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with batch, ec2, iam, and ecs access. Works with Terraform aws_batch_compute_environment / aws_batch_job_queue / aws_batch_job_definition resources and CloudFormation AWS::Batch::ComputeEnvironment / AWS::Batch::JobQueue / AWS::Batch::JobDefinition templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, batch, compute-environment, cloudops, deploy, compute, provisioning, job-queue, job-definition, spot, fargate
  dependencies: aws-orchestrator
  keywords: aws, batch, compute environment, job queue, job definition, cloudops, deploy, provisioning, allocation strategy, spot, fargate, eks, array jobs, job dependencies
  when_to_use: Invoke when the user wants to create an AWS Batch compute environment (EC2, Fargate, or EKS), set up a job queue with priority levels, register a job definition with container and resource specifications, configure spot instance integration, use allocation strategies (BEST_FIT, BEST_FIT_PROGRESSIVE, SPOT_CAPACITY_OPTIMIZED), or configure array jobs with dependencies. Do NOT invoke for ECS task definitions (use ecs-fargate-deployer), EKS cluster creation (use eks skills), or Lambda functions (use lambda skills).
---

# Batch Compute Environment Deployer

An AWS CloudOps agent skill that provisions AWS Batch compute
environments, job queues, and job definitions with correct defaults.
The skill walks the operator through EC2 vs Fargate vs EKS compute
environment selection, launch template integration, allocation strategy
decisions, instance types and roles, min/max/desired vCPUs, subnet and
security group configuration, job queue creation with priority levels,
job definition specification, job dependencies, array jobs, scheduling
priority, CloudWatch metrics, and spot instance integration, captures
workload and scaling decisions, explains why each default matters, and
emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create Batch compute environment, Batch job queue, register job
definition, Batch allocation strategy, Batch spot capacity, Batch
Fargate, Batch array jobs, Batch job dependencies.

## STRICT output contract

When this skill is invoked with a Batch-provisioning request (create a
compute environment, set up a job queue, register a job definition,
configure spot instances for Batch, use allocation strategies, or set
up array jobs with dependencies), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `BATCH_COMPUTE:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

### Decision tree leading to the output

```text
1. Is the compute environment type specified?
   ├─ EC2  → go to 2
   ├─ Fargate → skip to 3 (no allocation strategy, no launch template)
   └─ EKS  → go to 2 (also requires EKS cluster ARN)
2. Is the request spot-based?
   ├─ YES → allocationStrategy MUST be SPOT_CAPACITY_OPTIMIZED
   │        type MUST be SPOT; spotIamFleetRole REQUIRED
   │        → 3+ instance types for pool diversity
   └─ NO  → allocationStrategy = BEST_FIT_PROGRESSIVE (≥2 types)
            or BEST_FIT (single type, predictable capacity)
3. Is the job queue referencing at least one ENABLED CE?
   ├─ YES → VERDICT: READY_TO_DEPLOY
   └─ NO  → VERDICT: PREREQUISITES_MISSING ([✗] State: DISABLED)
4. Does the job definition's vCPU/memory fit the largest instance type?
   ├─ YES → emit CHECKLIST with [✓] on every line
   └─ NO  → VERDICT: PREREQUISITES_MISSING ([✗] Job definition: vCPU
            request exceeds largest instance type capacity)
5. Emit VERIFICATION_COMMANDS using the actual names from CHECKLIST.
```

### FORBIDDEN output patterns

1. **NEVER preface the block with prose, greetings, or "Here is your...".**
   The first line of the response MUST be `BATCH_COMPUTE:`.
2. **NEVER emit `VERDICT: READY_TO_DEPLOY` when any CHECKLIST line is
   `[✗]`.** A single `[✗]` forces `VERDICT: PREREQUISITES_MISSING`.
3. **NEVER use placeholder text** (`<env-name>`, `your-queue`, `XXX`)
   in a worked example. Use real names, real ARNs, real instance types.
4. **NEVER omit the `State: ENABLED` line.** Creating a CE does NOT
   enable it; the #1 Batch failure is a DISABLED CE blocking jobs.
5. **NEVER list `SPOT_CAPACITY_OPTIMIZED` for an On-Demand environment
   or `BEST_FIT` for a spot environment.** Strategy MUST match type.
6. **NEVER emit a job queue without listing its compute environments
   and priority.** A queue with no ENABLED CE is a silent failure.
7. **NEVER omit VERIFICATION_COMMANDS.** The block is incomplete
   without copy-pasteable `aws batch describe-*` commands.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Compute environment type (EC2 vs Fargate vs EKS) | Core model |
| Step 2 — Allocation strategy | Instance selection |
| Step 3 — Launch template integration | Custom AMI / userdata |
| Step 4 — Instance types, role, min/max/desired vCPUs | Capacity |
| Step 5 — Subnet and security group configuration | Networking |
| Step 6 — Job queue creation with priority levels | Queue |
| Step 7 — Job definition (container, vCPU, memory, resources) | Job spec |
| Step 8 — Job dependencies and array jobs | DAG |
| Step 9 — Spot instance integration | Spot capacity |
| Step 10 — CloudWatch metrics and scheduling priority | Observability |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/allocation-strategies.md | Allocation strategy detail |
| references/job-definitions-and-queues.md | Job def + queue detail |

## Mindset

**One-line takeaway:** AWS Batch has three layers: compute environment
(infrastructure), job queue (priority-ordered routing), and job
definition (container + resource spec). A compute environment MUST be
ENABLED and a job queue MUST reference it before jobs can run.
Allocation strategy is the #1 lever for cost optimization and capacity
availability.

Three misconceptions dominate Batch misdesign at provisioning time:

- **"BEST_FIT is always the right allocation strategy."** It is not.
  BEST_FIT packs jobs tightly onto the fewest instances, which minimizes
  cost but can cause capacity starvation when instance types are scarce.
  BEST_FIT_PROGRESSIVE scales out additional instance types when the
  primary type is unavailable. SPOT_CAPACITY_OPTIMIZED should be used
  for spot-based compute environments to reduce interruption risk.

- **"A job queue with one compute environment is enough."** Production
  workloads should have at least two compute environments attached to a
  job queue: an On-Demand environment (high priority, guaranteed
  throughput) and a Spot environment (lower priority, cost-efficient
  burst). The queue priority weighting determines scheduling order.

- **"Fargate is always cheaper than EC2 for Batch."** Fargate charges a
  per-vCPU and per-GB-memory premium. For sustained workloads, EC2 with
  BEST_FIT_PROGRESSIVE is typically 40-60% cheaper. Fargate is better
  for sporadic, short-lived jobs where infra management overhead
  outweighs the savings.

## Configuration dependency graph (novel heuristic)

Batch configurations are NOT independent. The compute environment must
be ENABLED before a job queue can reference it. The job queue must
exist before jobs can be submitted. The job definition must specify
resource requirements satisfiable by the compute environment's instance
types.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Service-linked role | none (auto-created on first use) | if deleted, Batch API calls fail | Batch API access |
| Compute environment (EC2) | instance role with ecs trust; subnets; SGs | starts DISABLED — must be ENABLED before jobs run | job queue attachment |
| Compute environment (Fargate) | subnets; security groups | max vCPUs required; no instance role needed | job queue attachment |
| Compute environment (EKS) | EKS cluster exists; EKS compute role | EKS cluster must be same region | job queue attachment |
| Job queue | at least one ENABLED compute environment | priority (1-1000) controls scheduling | job submission |
| Job definition | container image in ECR; vCPU/memory specified | resource requirements must fit instance types | job submission |
| Job dependencies | dependent jobs must exist | SEQUENTIAL waits for ALL children; N-ARY waits for N | DAG scheduling |
| Array jobs | job definition with arrayProperties | array size limit 10000; children are independent | parallel fan-out |
| Spot integration | type MANAGED + SPOT_CAPACITY_OPTIMIZED | spot instances can be interrupted; be idempotent | cost-optimized compute |
| Launch template | EC2 launch template exists | overrides AMI, userdata, EBS settings | custom AMI / userdata |

**The compute-environment-must-be-ENABLED row is the one a baseline
model misses.** Creating a compute environment does NOT enable it. A
job queue referencing a DISABLED compute environment will not schedule
jobs — they sit in RUNNABLE indefinitely.

**Cross-dependency gotchas:**
- A job requesting 8 vCPUs cannot run on a compute environment whose
  largest instance type offers 4 vCPUs — it stays in RUNNABLE forever.
- A job queue tries compute environments in order (1, 2, ...). This is
  the basis for Spot primary + On-Demand fallback.
- Array children are independent jobs; they may land on different
  instances and execute in any order.
- Fargate does NOT support launch templates, spot, or allocation
  strategies — it is always On-Demand.
- EKS compute environments require the Batch service role to have EKS
  permissions.

## Expert heuristic: BEST_FIT_PROGRESSIVE for heterogeneous pools

A baseline model says "use BEST_FIT." The correct heuristic recognizes
that BEST_FIT causes capacity starvation when the primary type is scarce.

```text
Instance pool: m5.large, m5.xlarge, m5.2xlarge, c5.large, c5.xlarge

BEST_FIT:
  → Packs onto fewest instances (lowest cost)
  → If m5.large unavailable, jobs WAIT (RUNNABLE stuck)
  → Good for: single instance type, predictable capacity

BEST_FIT_PROGRESSIVE:
  → Tries m5.large first; falls back to m5.xlarge, c5.large, etc.
  → Scales across MULTIPLE types simultaneously
  → Good for: heterogeneous pools, production workloads

SPOT_CAPACITY_OPTIMIZED:
  → Selects spot pools with most spare capacity
  → Minimizes interruption risk (not cost)
  → Good for: spot-based environments
```

**Key implication:** BEST_FIT_PROGRESSIVE is almost always the right
choice for EC2 environments with multiple instance types. Use
SPOT_CAPACITY_OPTIMIZED only for spot-based environments.

## Expert heuristic: job dependency DAG and queue priority weighting

A baseline model submits jobs individually. The correct heuristic uses
dependency graphs (DAGs) and queue priority for workload tiering.

```text
Job dependency DAG:

  [Stage 1: Ingest]  ingest-001, ingest-002 (no deps)
         │
         ▼ (dependsOn: [ingest-001, ingest-002])
  [Stage 2: Transform]  transform-001
         │
         ▼ (dependsOn: [transform-001])
  [Stage 3: Load]  load-001

Dependency types:
  SEQUENTIAL → waits for ALL children of previous job
  N_TO_N     → waits for N specified children
  ARRAY      → waits for all array children of a parent

Queue priority weighting (1-1000, higher = first):
  Queue "critical"  priority: 1000 → On-Demand env (guaranteed)
  Queue "default"   priority: 500  → Spot env (cost-efficient)
  Queue "batch"     priority: 1    → Spot env (best-effort)
```

**Key implication:** use SEQUENTIAL for pipeline stages, N_TO_N for
fan-in, and queue priority for workload tiering.

## Expert heuristic: spot capacity optimization fallback

A baseline model uses spot without a fallback. The correct heuristic
pairs Spot + On-Demand compute environments in the same queue.

```text
Job Queue: production-queue (priority: 500)
  ├── CE 1 (order 1): spot-env — SPOT_CAPACITY_OPTIMIZED, max 1000 vCPUs
  └── CE 2 (order 2): ondemand-env — BEST_FIT_PROGRESSIVE, max 200 vCPUs

Behavior:
  → Batch tries spot-env first
  → If spot exhausted, jobs fall through to ondemand-env
  → On-Demand guarantees minimum throughput during spot disruption
```

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Batch service-linked role | Batch needs AWSServiceRoleForBatch | `aws iam get-role --role-name AWSServiceRoleForBatch` |
| Instance role (EC2) with ECS trust | EC2 instances need ecs:RegisterContainerInstance | `aws iam get-role --role-name <instance-role>` |
| Subnets identified | Compute environment needs subnet IDs | `aws ec2 describe-subnets` |
| Security group identified | Instances need a security group | `aws ec2 describe-security-groups` |
| Container image in ECR | Job definition references an image | `aws ecr describe-images --repository-name <repo>` |
| Instance types valid for region | Not all types exist in all regions | `aws ec2 describe-instance-types` |
| EKS cluster exists (if EKS) | EKS environment references a cluster | `aws eks describe-cluster --name <cluster>` |
| Launch template (if specified) | CE references a launch template | `aws ec2 describe-launch-templates` |

## Step 1 — Compute environment type (EC2 vs Fargate vs EKS)

| Feature | EC2 | Fargate | EKS |
|---|---|---|---|
| Infrastructure | Batch manages EC2 instances | Serverless | Batch manages pods on EKS |
| Instance types | Operator specifies | Abstracted | Operator specifies EKS nodes |
| Allocation strategy | BEST_FIT, BEST_FIT_PROGRESSIVE, SPOT_CAPACITY_OPTIMIZED | N/A (On-Demand) | BEST_FIT, BEST_FIT_PROGRESSIVE |
| Spot support | Yes | No | Yes |
| Launch template | Yes | No | No |
| GPU workloads | Yes (g4dn, p3, p4) | No | Yes |
| Cost (sustained) | Lowest | Highest | Medium |
| Best for | Sustained, GPU, spot | Sporadic, short-lived | Kubernetes-native |

**EC2** is most flexible and cost-effective for sustained workloads.
**Fargate** is simplest for sporadic jobs (no spot, no GPUs, no launch
templates). **EKS** consolidates compute for Kubernetes-native shops.

## Step 2 — Allocation strategy

| Strategy | Behavior | When to use | Spot |
|---|---|---|---|
| BEST_FIT | Fewest instances; waits if primary type unavailable | Single type, predictable | No |
| BEST_FIT_PROGRESSIVE | Primary first; falls back to other types | Heterogeneous pools, production | No |
| SPOT_CAPACITY_OPTIMIZED | Spot pools with most spare capacity | Spot-based environments | Yes |

BEST_FIT_PROGRESSIVE is the default for EC2 production environments.
SPOT_CAPACITY_OPTIMIZED is required for spot-based environments.

## Step 3 — Launch template integration

A launch template customizes EC2 instances: custom AMI, user data, EBS
volumes, IMDSv2, and more.

```bash
# Create a launch template for Batch
aws ec2 create-launch-template \
  --launch-template-name batch-custom-lt \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "BlockDeviceMappings": [{"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 100, "VolumeType": "gp3", "Encrypted": true}}],
    "MetadataOptions": {"HttpTokens": "required"}
  }'
```

Reference it in the compute environment via `launchTemplate:
{launchTemplateName: "batch-custom-lt", version: "$Default"}`.
Launch templates are only supported for EC2 compute environments.

## Step 4 — Instance types, role, min/max/desired vCPUs

| Parameter | Purpose | Recommendation |
|---|---|---|
| `instanceTypes` | Types Batch can provision | 3+ types for BEST_FIT_PROGRESSIVE |
| `instanceRole` | IAM instance profile | Must have ecs trust + SSM + CloudWatch |
| `minvCpus` | Minimum always-provisioned capacity | 0 for cost-optimized; >0 for guaranteed |
| `maxvCpus` | Maximum capacity cap | Set based on budget |
| `desiredvCpus` | Initial capacity (Batch auto-adjusts) | Usually 0 |

**Critical:** the `instanceRole` must have a trust policy allowing
`ecs.amazonaws.com` to assume it. Without this, instances cannot
register with the ECS agent and jobs never start.

## Step 5 — Subnet and security group configuration

| Parameter | Purpose | Consideration |
|---|---|---|
| `subnets` | Where Batch provisions instances | Use private subnets; NAT gateway for ECR pulls |
| `securityGroupIds` | Firewall rules | Allow outbound 443 for ECR + CloudWatch |

**Common mistake:** specifying only public subnets. Batch instances
should be in private subnets with a NAT gateway for outbound traffic.
For Fargate, subnets must be in the same VPC.

## Step 6 — Job queue creation with priority levels

A job queue routes jobs to one or more compute environments. The
priority (1-1000) determines scheduling order when queues compete.

```bash
aws batch create-job-queue \
  --job-queue-name production-queue \
  --state ENABLED \
  --priority 500 \
  --compute-environment-order \
    '[{"order":1,"computeEnvironment":"batch-spot-env"},
      {"order":2,"computeEnvironment":"batch-ondemand-env"}]'
```

**Priority semantics:** higher = scheduled first. Jobs do NOT preempt
running jobs; they get capacity at the next scaling cycle. Two queues
with the same priority compete fairly (round-robin).

**Compute environment order:** Batch tries order 1 first; if at max
vCPUs, jobs fall through to order 2. Production pattern: Spot (order 1)
+ On-Demand (order 2).

## Step 7 — Job definition (container, vCPU, memory, resources)

```bash
aws batch register-job-definition \
  --job-definition-name data-pipeline-v1 \
  --type container \
  --container-properties '{
    "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/data-pipeline:latest",
    "vcpus": 4,
    "memory": 8192,
    "command": ["python", "/app/process.py", "--batch-size", "1000"],
    "jobRoleArn": "arn:aws:iam::123456789012:role/BatchJobRole",
    "executionRoleArn": "arn:aws:iam::123456789012:role/BatchExecutionRole",
    "environment": [
      {"name": "S3_BUCKET", "value": "my-data-bucket"},
      {"name": "LOG_LEVEL", "value": "INFO"}
    ],
    "mountPoints": [{"containerPath": "/mnt/data", "sourceVolume": "efs-data"}],
    "volumes": [{"name": "efs-data", "efsVolumeConfiguration": {"fileSystemId": "fs-abc12345", "rootDirectory": "/data"}}],
    "logConfiguration": {"logDriver": "awslogs", "options": {"awslogs-group": "/aws/batch/data-pipeline", "awslogs-stream-prefix": "batch"}},
    "fargatePlatformConfiguration": {"platformVersion": "LATEST"}
  }' \
  --platform-capabilities EC2 FARGATE
```

**Critical resource matching:**
- vCPUs and memory must be satisfiable by the compute environment's
  instance types. A job requesting 8 vCPUs cannot run on 2-vCPU types.
- For Fargate, vCPUs/memory must match supported combinations.
- GPU jobs require GPU instance types (g4dn, p3, p4) and
  `resourceRequirements: [{"type": "GPU"}]`.

## Step 8 — Job dependencies and array jobs

**Sequential dependency:**

```bash
aws batch submit-job --job-queue production-queue \
  --job-definition data-pipeline-v1 --job-name transform-step \
  --depends-on '[{"jobId": "ingest-job-id-123"}]'
```

**Array job (fan-out parallelism):**

```bash
aws batch submit-job --job-queue production-queue \
  --job-definition data-pipeline-v1 --job-name parallel-transform \
  --array-properties '{"size": 100}'
```

Each array child gets `AWS_BATCH_JOB_ARRAY_INDEX` (0 to 99) for work
partitioning. Array size limit: 10000. To depend on array completion,
use `{"jobId": "parent-id", "type": "N_TO_N"}`.

## Step 9 — Spot instance integration

```bash
aws batch create-compute-environment \
  --compute-environment-name batch-spot-env \
  --type MANAGED --state ENABLED \
  --compute-resources '{
    "type": "SPOT",
    "allocationStrategy": "SPOT_CAPACITY_OPTIMIZED",
    "minvCpus": 0, "maxvCpus": 1000, "desiredvCpus": 0,
    "instanceTypes": ["m5.large", "m5.xlarge", "c5.large", "c5.xlarge", "r5.large"],
    "subnets": ["subnet-aaa11122", "subnet-bbb22233"],
    "securityGroupIds": ["sg-batch111"],
    "instanceRole": "arn:aws:iam::123456789012:instance-profile/batch-instance-profile",
    "spotIamFleetRole": "arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet"
  }' \
  --service-role arn:aws:iam::123456789012:role/AWSBatchServiceRole
```

**Requirements:** type `SPOT`, allocation `SPOT_CAPACITY_OPTIMIZED`,
`spotIamFleetRole` referencing the EC2 Spot Fleet role. Use 3+ instance
types for pool diversity. Jobs should be idempotent (2-min interruption
warning).

## Step 10 — CloudWatch metrics and scheduling priority

| Metric | Measures | Action |
|---|---|---|
| `CpuUtilization` (CPUPct) | Avg CPU across environment | Scale up if > 80% sustained |
| `MemoryUtilization` (MemoryPct) | Avg memory | Investigate if > 90% (OOM) |
| `RUNNABLE` count | Jobs waiting for capacity | Alert if > 0 for > 15 min |

**Detecting capacity starvation** (the #1 Batch issue):

```bash
# Check for RUNNABLE jobs
aws batch list-jobs --job-queue production-queue --job-status RUNNABLE

# Check compute environment status
aws batch describe-compute-environments --compute-environments batch-ec2-env
```

Common causes of RUNNABLE stuck: job requests more vCPUs than any
instance type provides, instance role trust policy broken, security
group blocks outbound 443, subnet has no available IPs, or maxvCpus too
low.

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **Batch on EKS (2023-2024):** Batch jobs as Kubernetes pods on
  existing EKS clusters. Requires EKS compute environment type.
- **Fargate platform LATEST (2023-2024):** Auto-uses newest Fargate
  platform without pinning versions.
- **SPOT_CAPACITY_OPTIMIZED enhancements (2023-2024):** Improved pool
  selection reducing interruption rates up to 30%.
- **Step Functions orchestration (2024-2025):** Native Batch integration
  with Dynamic ItemProcessor for large-scale parallel workflows.
- **EFS access points (2024-2025):** Fine-grained access control for
  shared file systems in job definitions.
- **Cost allocation tags (2024-2025):** Per-workload cost tracking via
  tags on compute environments and job queues.

## NEVER do these things

1. **NEVER leave a compute environment in DISABLED state.** Creating it
   does NOT enable it. Jobs to a queue referencing a DISABLED CE sit in
   RUNNABLE indefinitely. Always verify `state: ENABLED`.

2. **NEVER use BEST_FIT for heterogeneous instance pools.** It waits if
   the primary type is unavailable. Use BEST_FIT_PROGRESSIVE for pools
   with 2+ instance types.

3. **NEVER request more vCPUs in a job definition than the compute
   environment's largest instance type provides.** The job will be
   permanently stuck in RUNNABLE with no error.

4. **NEVER mix allocation strategies incorrectly.** Spot requires
   SPOT_CAPACITY_OPTIMIZED. On-Demand uses BEST_FIT or
   BEST_FIT_PROGRESSIVE.

5. **NEVER forget the instance role trust policy for EC2.** The instance
   role must allow `ecs.amazonaws.com` to assume it. Without this,
   instances cannot register and jobs never start.

6. **NEVER use public subnets for Batch instances.** Use private subnets
   with a NAT gateway. Public subnets expose instances to the internet.

7. **NEVER submit jobs to a queue with zero ENABLED compute
   environments.** The job will sit in RUNNABLE forever.

8. **NEVER assume array children execute in order.** Each child is
   independent and may start/finish in any order. Use
   `AWS_BATCH_JOB_ARRAY_INDEX` to partition work.

9. **NEVER use Fargate for GPU workloads.** Fargate does not support
   GPUs. GPU jobs require EC2 with GPU instance types.

10. **NEVER set `maxvCpus` arbitrarily high without cost analysis.**
    Batch scales to max if there are RUNNABLE jobs. Set based on budget.

## Output format

```text
BATCH_COMPUTE: <compute-environment-name> (<type>, <allocation-strategy>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Compute environment type: EC2 | Fargate | EKS
  [✓|✗] Compute environment name: <name>
  [✓|✗] State: ENABLED | DISABLED
  [✓|✗] Allocation strategy: BEST_FIT | BEST_FIT_PROGRESSIVE | SPOT_CAPACITY_OPTIMIZED
  [✓|✗] Instance types: <list>
  [✓|✗] Instance role: <role-arn> (EC2 only)
  [✓|✗] Launch template: <lt-name> (EC2 only) | N/A
  [✓|✗] Min vCPUs: <n>, Max vCPUs: <n>, Desired vCPUs: <n>
  [✓|✗] Subnets: <list>
  [✓|✗] Security groups: <list>
  [✓|✗] Spot fleet role: <role-arn> (spot only) | N/A
  [✓|✗] Job queue: <queue-name> (priority: <n>, compute environments: <list>)
  [✓|✗] Job definition: <name>:<revision> (image: <image>, vCPUs: <n>, memory: <n> MB)
  [✓|✗] Job dependencies: none | sequential | N-ary | array (size: <n>)
  [✓|✗] CloudWatch metrics: CPUPct, MemoryPct, RUNNABLE count
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws batch describe-compute-environments --compute-environments <env-name>
  aws batch describe-job-queues --job-queues <queue-name>
  aws batch describe-job-definitions --job-definition-name <def-name>
```

### Worked example — EC2 with BEST_FIT_PROGRESSIVE

```text
BATCH_COMPUTE: batch-ec2-env (EC2, BEST_FIT_PROGRESSIVE)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Compute environment type: EC2
  [✓] Compute environment name: batch-ec2-env
  [✓] State: ENABLED
  [✓] Allocation strategy: BEST_FIT_PROGRESSIVE
  [✓] Instance types: m5.large, m5.xlarge, m5.2xlarge
  [✓] Instance role: arn:aws:iam::123456789012:instance-profile/batch-instance-profile
  [✓] Launch template: batch-custom-lt ($Default)
  [✓] Min vCPUs: 0, Max vCPUs: 256, Desired vCPUs: 0
  [✓] Subnets: subnet-aaa11122, subnet-bbb22233
  [✓] Security groups: sg-batch111
  [✓] Spot fleet role: N/A
  [✓] Job queue: production-queue (priority: 500, compute environments: batch-ec2-env)
  [✓] Job definition: data-pipeline-v1:1 (image: data-pipeline:latest, vCPUs: 4, memory: 8192 MB)
  [✓] Job dependencies: none
  [✓] CloudWatch metrics: CPUPct, MemoryPct, RUNNABLE count
  [✓] Tags: Environment=production, Workload=data-pipeline
VERIFICATION_COMMANDS:
  aws batch describe-compute-environments --compute-environments batch-ec2-env
  aws batch describe-job-queues --job-queues production-queue
  aws batch describe-job-definitions --job-definition-name data-pipeline-v1
```

### Worked example — Spot CE with SPOT_CAPACITY_OPTIMIZED + On-Demand fallback

```text
BATCH_COMPUTE: batch-spot-env (EC2, SPOT_CAPACITY_OPTIMIZED)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Compute environment type: EC2 (SPOT)
  [✓] Compute environment name: batch-spot-env
  [✓] State: ENABLED
  [✓] Allocation strategy: SPOT_CAPACITY_OPTIMIZED
  [✓] Instance types: m5.large, m5.xlarge, c5.large, c5.xlarge, r5.large
  [✓] Instance role: arn:aws:iam::123456789012:instance-profile/batch-instance-profile
  [✓] Launch template: N/A (spot does not require LT)
  [✓] Min vCPUs: 0, Max vCPUs: 1000, Desired vCPUs: 0
  [✓] Subnets: subnet-aaa11122, subnet-bbb22233
  [✓] Security groups: sg-batch111
  [✓] Spot fleet role: arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet
  [✓] Job queue: production-queue (priority: 500, compute environments:
        order 1: batch-spot-env, order 2: batch-ondemand-env)
  [✓] Job definition: ml-training-v3:7 (image:
        123456789012.dkr.ecr.us-east-1.amazonaws.com/ml-training:3.7,
        vCPUs: 8, memory: 16384 MB, GPU: N/A)
  [✓] Job dependencies: array (size: 100, N_TO_N on completion)
  [✓] CloudWatch metrics: CPUPct, MemoryPct, RUNNABLE count, SpotInterruption
  [✓] Tags: Environment=production, Workload=ml-training, SpotOptimized=true
VERIFICATION_COMMANDS:
  aws batch describe-compute-environments --compute-environments batch-spot-env batch-ondemand-env
  aws batch describe-job-queues --job-queues production-queue
  aws batch describe-job-definitions --job-definition-name ml-training-v3
  aws batch list-jobs --job-queue production-queue --job-status RUNNABLE
```

The spot example above demonstrates the production pattern: spot CE at
order 1 (cost-efficient burst) + On-Demand CE at order 2 (guaranteed
floor). If spot capacity is exhausted, jobs fall through to On-Demand
automatically. Jobs MUST be idempotent because spot instances receive
a 2-minute interruption warning.

## Error handling

### Jobs stuck in RUNNABLE
- Capacity starvation. Verify the job's vCPU/memory request fits the
  instance types. Check state=ENABLED, status=VALID. Check instance role
  trust policy, subnet IPs, and security group outbound 443.

### Compute environment INVALID
- Check `statusReason` in `describe-compute-environments`. Common causes:
  invalid instance role, missing subnets, insufficient permissions.

### Spot instances continuously interrupted
- Pool too narrow. Add more instance types. Verify
  SPOT_CAPACITY_OPTIMIZED. Consider an On-Demand fallback environment.

### Fargate jobs fail to start
- Verify subnets are in the same VPC as security groups. Ensure
  execution role has `ecs-tasks.amazonaws.com` trust and
  `AmazonECSTaskExecutionRolePolicy`.

## Domain

AWS CloudOps / AWS Batch Compute Environment, Job Queue, and Job
Definition Provisioning & Workload Scheduling.

## AWS documentation

- **AWS Batch User Guide** — https://docs.aws.amazon.com/batch/latest/userguide/what-is-batch.html
- **Compute environments** — https://docs.aws.amazon.com/batch/latest/userguide/compute_environments.html
- **Allocation strategies** — https://docs.aws.amazon.com/batch/latest/userguide/allocation-strategies.html
- **Job queues** — https://docs.aws.amazon.com/batch/latest/userguide/job_queues.html
- **Job definitions** — https://docs.aws.amazon.com/batch/latest/userguide/job_definitions.html
- **Job dependencies** — https://docs.aws.amazon.com/batch/latest/userguide/using_job_dependencies.html
- **Array jobs** — https://docs.aws.amazon.com/batch/latest/userguide/array_jobs.html
- **Spot instances in Batch** — https://docs.aws.amazon.com/batch/latest/userguide/spot_instances.html
- **Batch on EKS** — https://docs.aws.amazon.com/batch/latest/userguide/eks.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/batch/latest/userguide/cloudwatch_metrics.html
