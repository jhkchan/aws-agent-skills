# End-to-end usage scenario: ecs-task-troubleshooter

A walkthrough showing the skill diagnosing an ECS service crash-loop
caused by a secret-injection failure. This exercises Step 1 (symptom
identification), Step 3 (essential container exit), Step 6 (crash
loop pattern), the deployment circuit breaker context, and the
remediation workflow.

## Input (user prompt)

> Our `api-svc` on the `prod-app` Fargate cluster is crash-looping.
> Tasks stop within 2 seconds of starting. The deployment circuit
> breaker has not yet fired but will soon. CloudWatch Logs has a
> single line per failed task:
> `ResourceInitializationError: unable to retrieve secrets: 1 error
> occurred: AccessDeniedException ... secretsmanager:GetSecretValue
> ... db-password-AbCdEf`.

## Skill output

```text
TARGET: cluster prod-app / service api-svc / task arn:aws:ecs:us-east-1:111111111111:task/prod-app/6f8a...
VERDICT: ROOT_CAUSE_IDENTIFIED
ROOT_CAUSE: CONFIG_EXECUTION_ROLE
REASON: Secret injection failed because the execution role lacks
  secretsmanager:GetSecretValue on the referenced secret ARN. The
  container exited before the application process started (exit code
  1, empty container reason). The ECS agent runs the secret fetch
  during PROVISIONING using the execution role, so this is NOT a task
  role issue.
EVIDENCE:
  - describe-tasks: lastStatus STOPPED, stoppedReason "Essential
    container in task exited", startedAt→stoppedAt ~2 seconds,
    containers[0].exitCode 1, containers[0].reason empty
  - CloudWatch Logs (only line): "ResourceInitializationError: unable
    to retrieve secrets: AccessDeniedException ... is not authorized
    to perform secretsmanager:GetSecretValue on resource
    arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-AbCdEf"
  - describe-task-definition: secrets[] references
    arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-AbCdEf
  - Execution role inline policy: only logs:CreateLogStream +
    logs:PutLogEvents; no secretsmanager:GetSecretValue
  - simulate-principal-policy on the execution role against
    secretsmanager:GetSecretValue on the secret ARN: implicitDeny
  - Passing: ECR endpoint and S3 gateway are present (image pull is
    not the issue); subnet has 22 free IPs (ENI is not the issue).
REMEDIATION:
  1. Add a statement to the execution role's inline policy:
     {
       "Effect": "Allow",
       "Action": "secretsmanager:GetSecretValue",
       "Resource": "arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-*"
     }
     Note the trailing `-*` wildcard — this accommodates the
     6-character random suffix that rotates when the secret is rotated.
     Pin to the exact ARN only if immutability is required.
  2. Verify with:
     aws iam simulate-principal-policy \
       --policy-source-arn arn:aws:iam::111111111111:role/ecsTaskExecutionRole \
       --action-names secretsmanager:GetSecretValue \
       --resource-arns arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-AbCdEf
     Expect: allowed.
  3. Register a new task definition revision (no change needed to the
     task definition itself — the IAM update is the fix), then run a
     one-off task to verify:
     aws ecs run-task --cluster prod-app \
       --task-definition api-svc-task --count 1 --launch-type FARGATE \
       --network-configuration awsvpcConfiguration=...
  4. If the verification task reaches RUNNING and stays healthy for
     60+ seconds, the deployment circuit breaker will recover on its
     own at the next scheduler retry. If the service is in a
     deployment-stuck state, force a new deployment:
     aws ecs update-service --cluster prod-app --service api-svc \
       --force-new-deployment
  5. Monitor CloudTrail for further AccessDenied events on
     secretsmanager:GetSecretValue over the next hour.
```

## What the skill caught that a generic assistant misses

1. **The exit-code-1-with-empty-reason signature.** A generic
   assistant often attributes "exit code 1" to "application error." The
   skill recognises that an empty container reason + a
   ResourceInitializationError log line means the container never
   started — the failure is in the secret injection phase, before the
   container process runs.

2. **The execution role vs task role distinction.** Secret injection
   uses the EXECUTION role (the ECS agent's role for pulling images and
   reading secrets), NOT the task role (the application's runtime
   role). A generic assistant often recommends adding the permission to
   the task role, which has no effect — the application container never
   sees the secret because injection failed before it started.

3. **The 6-character random suffix wildcard.** A generic assistant
   typically scopes the new permission to the exact ARN, which works
   today but breaks on the next secret rotation. The skill scopes with
   `db-password-*` to absorb the suffix change.

4. **The deployment circuit breaker context.** The skill notes that the
   service has not yet rolled back and explains how the fix interacts
   with the circuit breaker — the next scheduler retry will pick up the
   IAM change automatically.

## Slash-command invocation

```
/aws:troubleshoot-ecs-task
```

Or via the orchestrator:

```
/aws:pipeline
You: "api-svc on prod-app is crash-looping, tasks stop in 2 seconds"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
ecs-task-troubleshooter]` and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "ECS service crash-loop, tasks exit in 2 seconds"
# [Phase: Troubleshoot | Skills routed: ecs-task-troubleshooter]
```

## Live-account diagnostic flow (requires AWS CLI)

When the operator has credentials for the failing account:

```bash
# Identify the most recently stopped task for the service.
aws ecs list-tasks --cluster prod-app --service-name api-svc \
  --desired-status STOPPED --max-items 1

# Read the full stoppedReason + container exit codes.
aws ecs describe-tasks --cluster prod-app \
  --tasks arn:aws:ecs:us-east-1:111111111111:task/prod-app/<id> \
  --query 'tasks[0].{stoppedReason:stoppedReason,containers:containers[*].{name:name,exitCode:exitCode,reason:reason}}'

# Read the execution role policy to confirm the missing permission.
aws iam list-role-policies --role-name ecsTaskExecutionRole
aws iam get-role-policy --role-name ecsTaskExecutionRole \
  --policy-name <inline-policy-name>

# Simulate the execution role to confirm the implicit deny.
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/ecsTaskExecutionRole \
  --action-names secretsmanager:GetSecretValue \
  --resource-arns arn:aws:secretsmanager:us-east-1:111111111111:secret:db-password-AbCdEf
```

If `simulate-principal-policy` returns `implicitDeny`, the diagnosis
is confirmed without needing to read CloudTrail. The fix is to update
the execution role's inline policy or attach a managed policy that
includes `secretsmanager:GetSecretValue` on the secret ARN.
