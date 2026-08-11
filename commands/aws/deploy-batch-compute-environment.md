---
name: deploy-batch-compute-environment
description: Deploy AWS Batch compute environments, job queues, and job definitions
---

# Deploy AWS Batch Compute Environment

Routes to the `batch-compute-environment-deployer` skill.

## Usage
```
/deploy-batch-compute-environment <description of what to deploy>
```

## Examples
- `/deploy-batch-compute-environment EC2 spot environment with on-demand fallback, production queue`
- `/deploy-batch-compute-environment Fargate compute environment for ETL with array jobs`

## Triggers
- aws batch
- compute environment
- job queue
- job definition
- allocation strategy
- BEST_FIT_PROGRESSIVE
- SPOT_CAPACITY_OPTIMIZED
- array jobs
- batch fargate
