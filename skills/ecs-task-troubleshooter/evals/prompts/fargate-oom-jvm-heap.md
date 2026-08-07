# Eval prompt: fargate-oom-jvm-heap

Diagnose the following ECS task failure. Walk the OOM diagnostic tree
(Step 4 of the decision tree) and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A Java (Spring Boot) container on Fargate is periodically OOM-killed.
The service runs on cluster `prod-app`, service `api-svc`.

## Known facts

- `describe-tasks` for the most recent failure:
  - `stoppedReason: "Essential container in task exited"`
  - `containers[0].exitCode: 137`
  - `containers[0].reason: "OOMKilled"`
  - `startedAt` ~2 hours before `stoppedAt`
- `describe-task-definition` for the failing revision:
  - `cpu: "512"` (0.5 vCPU)
  - `memory: "1024"` (1 GB — task-level)
  - container `memory: 1024` (matches task-level, Fargate)
- The Dockerfile CMD: `java -Xmx2g -jar /app/app.jar`
- CloudWatch Container Insights shows `MemoryUtilization` trending
  upward from ~50% to ~100% over the 2 hours before each crash.

## Symptom

The task runs for ~2 hours, then transitions to STOPPED with exit code
137. The pattern repeats for every new task.
