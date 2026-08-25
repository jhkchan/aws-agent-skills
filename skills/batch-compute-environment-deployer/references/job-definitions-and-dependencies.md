# Job Definitions & Dependencies

## Job Definition Structure
- containerProperties: image, vcpus, memory, command, environment, mountPoints, resourceRequirements
- retryStrategy: attempts (1-10), evaluateOnExit conditions
- timeout: attemptDurationSeconds
- propagateTags: true/false (tag inheritance from job to ECS task)
- schedulingPriority: 0-1000 (higher = more urgent, requires fair-share scheduling)

## Array Jobs
```json
{
  "arrayProperties": {
    "size": 100
  }
}
```
- Each child gets AWS_BATCH_JOB_ARRAY_INDEX environment variable
- Children run in parallel up to compute environment capacity
- Use for embarrassingly parallel workloads (ETL, rendering)

## Dependency Types
| Type | Behavior |
|---|---|
| SEQUENTIAL | Waits for previous job to complete (N_TO_N) |
| N_TO_N | Each child depends on corresponding child of parent |
| END_TO_END | Last child of parent must complete before any child starts |

## Cross-Job Dependencies
```json
{
  "dependsOn": [
    {"jobId": "ingest-job-id", "type": "SEQUENTIAL"}
  ]
}
```

## Job Queue Priority
- Priority: integer, higher = more urgent
- Within a queue, Batch schedules by priority then submission time
- Multiple CEs in a queue are tried in order (1 = primary)
- Fargate and EC2 CEs can coexist in the same queue

## CloudWatch Metrics
- CUMULATIVE metric: CPUPct (utilization across all jobs)
- QUEUE metric: JobsInRunnable (backlog indicator)
- JOB metric: JobExecutionTime (for timeout tuning)
---

## Expert heuristic: job dependency DAG and queue priority weighting (moved verbatim from SKILL.md)

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

---

## Step 7 — Job definition (container, vCPU, memory, resources): CLI (moved verbatim from SKILL.md)

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

