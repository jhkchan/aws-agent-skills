# Batch Compute Environment Deployer — secondary worked examples

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

### Worked example — Spot CE with SPOT_CAPACITY_OPTIMIZED + On-Demand fallback (moved verbatim from SKILL.md)

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

