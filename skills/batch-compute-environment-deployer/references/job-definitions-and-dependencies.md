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
