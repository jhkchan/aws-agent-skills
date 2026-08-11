# Eval prompt: fargate-spot-fault-tolerant

Optimise the following Fargate workload for cost. Walk all optimization
dimensions and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

## Scenario

An ECS service processes SQS messages on Fargate, running 100% On-Demand.

## Known facts

- Task definition: `worker:8`
  - CPU: `1024` (1 vCPU)
  - Memory: `2048` (2 GB)
  - Architecture: `x86_64`
- Service: 20 desired tasks, running 24/7
- All tasks on Fargate On-Demand (no capacity provider strategy)
- Workload: each task pulls messages from an SQS queue, processes them,
  and deletes the message. If a task is interrupted, the message
  returns to the queue after the visibility timeout (30 seconds).
  The workload is stateless and retriable.
- 14-day CloudWatch metrics:
  - CPUUtilization: average 55%, maximum 72%
  - MemoryUtilization: average 48%, maximum 60%
- Cost Explorer: $631/month (20 tasks x $31.57/task/month)

## Symptom

The team wants to reduce the monthly Fargate bill. The workload is
fault-tolerant — interrupted tasks simply reprocess the message on the
next poll.
