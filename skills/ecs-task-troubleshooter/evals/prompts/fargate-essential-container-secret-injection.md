# Eval prompt: fargate-essential-container-secret-injection

Diagnose the following ECS task failure. Walk the essential-container-exit
diagnostic tree and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

An ECS service on a Fargate cluster crashes immediately on task start.
Cluster: `prod-app`. Service: `api-svc`.

## Known facts

- `describe-tasks` for the failing task shows:
  - `lastStatus: STOPPED`
  - `desiredStatus: RUNNING`
  - `stoppedReason: "Essential container in task exited"`
  - `startedAt` and `stoppedAt` are ~2 seconds apart
  - `containers[0].exitCode: 1`
  - `containers[0].reason: ""` (empty — application never started)
- CloudWatch Logs has exactly one line for the failed container:
  ```
  ResourceInitializationError: unable to retrieve secrets: 1 error
  occurred: AccessDeniedException: User
  arn:aws:sts::111111111111:assumed-role/ecsTaskExecutionRole/...
  is not authorized to perform secretsmanager:GetSecretValue on
  resource arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-AbCdEf
  ```
- `describe-task-definition` for the failing revision shows the `secrets`
  array references
  `arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-AbCdEf`.
- The execution role (`ecsTaskExecutionRole`) has an inline policy with
  `logs:CreateLogStream` and `logs:PutLogEvents` but NO
  `secretsmanager:GetSecretValue`.

## Symptom

The task transitions from `RUNNING` to `STOPPED` within ~2 seconds of
starting, repeatedly. The service's deployment circuit breaker has not
yet rolled back.
