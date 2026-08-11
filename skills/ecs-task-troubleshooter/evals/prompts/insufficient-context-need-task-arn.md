# Eval prompt: insufficient-context-need-task-arn

Diagnose the following ECS task failure report. The user has provided
only a vague symptom — no task ARN, no stoppedReason, no exit code, no
CloudWatch Logs output. Emit the standard diagnostic block (TARGET,
VERDICT, ROOT_CAUSE, REASON, EVIDENCE, REMEDIATION). If the diagnostic
tree cannot proceed without more evidence, emit `INSUFFICIENT_DATA` and
list the missing inputs and the next probe to run.

## Scenario

A user reports: "my ECS service is broken, tasks keep stopping". They
mention the cluster name `prod-app` and the service name `api-svc`.

## What the user has provided

- Cluster name: `prod-app`
- Service name: `api-svc`

## What the user has NOT provided

- A specific task ARN.
- The `stoppedReason` or `lastStatus` from `describe-tasks`.
- The `containers[].exitCode` or `containers[].reason`.
- Any CloudWatch Logs output.
- The task definition family/revision.
- The launch type (Fargate vs EC2).
- Whether the issue is at PROVISIONING, RUNNING, or STOPPED.
- Whether the deployment circuit breaker has fired.
- Whether this is a new deployment or a previously-working service.
