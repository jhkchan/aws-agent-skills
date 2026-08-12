# Example usage: cloudwatch-logs-not-ingesting-troubleshooter

A walkthrough showing the skill diagnosing a Lambda function that runs
successfully but emits zero CloudWatch Logs, demonstrating the
symptom-to-layer triage, the IAM-vs-Lambda-auto-create decision (the
role is missing `logs:CreateLogGroup`), the evidence-backed
ROOT_CAUSE_IDENTIFIED verdict, and the `AWSLambdaBasicExecutionRole`
remediation.

## Input (user prompt)

> Our payments Lambda function fn-prod-processor was redeployed an
> hour ago. API Gateway is getting 200s back, but we cannot find any
> logs in CloudWatch. The log group /aws/lambda/fn-prod-processor
> does not exist. We've been debugging the application code for 40
> minutes assuming the function was swallowing errors — help us find
> out why no logs are appearing.

```text
FunctionName: fn-prod-processor
Runtime: nodejs20.x
Handler: index.handler
Execution role: arn:aws:iam::111111111111:role/fn-prod-processor-role
Last deploy: 1 hour ago (added VPC access)

Execution role attached policies:
  - AWSLambdaVPCAccessExecutionRole
  - inline: { app-access: { Effect: Allow, Action: [s3:GetObject],
      Resource: "*" } }

aws iam simulate-principal-policy for the role:
  logs:CreateLogGroup on log-group ARNs: IMPLICIT_DENY
  logs:CreateLogStream on log-group ARNs: IMPLICIT_DENY
  logs:PutLogEvents on log-group ARNs: IMPLICIT_DENY

aws logs describe-log-groups --log-group-name-prefix /aws/lambda/fn-prod-processor:
  logGroups: []

CloudWatch metrics (last hour):
  AWS/Lambda Invocations: 47
  AWS/Lambda Errors: 0
```

## Skill output

```text
TARGET: /aws/lambda/fn-prod-processor
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The Lambda execution role is missing logs:CreateLogGroup,
  logs:CreateLogStream, and logs:PutLogEvents on the /aws/lambda/*
  log group ARN. The Lambda service silently failed to auto-create
  /aws/lambda/fn-prod-processor on the first invocation after the
  redeploy; no logs have been ingested since. The application code
  is not swallowing errors — the logs are not being shipped because
  the role cannot create the log group.
LAYER: IAM_PERMISSIONS
EVIDENCE:
  - Symptom: fn-prod-processor returns 200 to API Gateway (47
    invocations, 0 errors in the last hour) but /aws/lambda/
    fn-prod-processor does not exist in describe-log-groups.
  - Probe: aws iam simulate-principal-policy for
    arn:aws:iam::111111111111:role/fn-prod-processor-role returns
    IMPLICIT_DENY for logs:CreateLogGroup, logs:CreateLogStream,
    and logs:PutLogEvents on the log-group ARN pattern.
  - Probe: aws logs describe-log-groups --log-group-name-prefix
    /aws/lambda/fn-prod-processor returns logGroups: [] (the log
    group was never created).
  - Passing: AWSLambdaVPCAccessExecutionRole IS attached (VPC ENI
    creation is fine — that is why the function runs); the
    application's own code is fine (Errors metric is 0). The
    AWSLambdaBasicExecutionRole managed policy is NOT attached —
    that is the missing permission set.
REMEDIATION:
  1. Attach AWSLambdaBasicExecutionRole to the execution role:
     aws iam attach-role-policy \
       --role-name fn-prod-processor-role \
       --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  2. Re-invoke the function once; the log group will auto-create on
     the next invocation.
  3. Verify with aws logs describe-log-groups --log-group-name-prefix
     /aws/lambda/fn-prod-processor (log group should now exist) and
     aws logs describe-log-streams --log-group-name
     /aws/lambda/fn-prod-processor (at least one stream should
     appear after the next invocation).
CONFIRM: Before attaching the managed policy, emit and await:
  "CONFIRM: About to attach AWSLambdaBasicExecutionRole to
   fn-prod-processor-role. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Distinguished "no logs" from "function failing."** A generic
   assistant says "check the application code for swallowed errors."
   The skill reads the Lambda metrics first: 47 invocations, 0
   errors — the function is succeeding. The logs are missing, not
   the successes.

2. **Used `simulate-principal-policy` before recommending.** The skill
   verifies all three required `logs:*` actions return IMPLICIT_DENY
   before declaring IAM the root cause. This is positive evidence,
   not a guess.

3. **Identified the specific missing managed policy.** The skill
   recognises that `AWSLambdaVPCAccessExecutionRole` IS attached (so
   VPC access works — the function runs) but
   `AWSLambdaBasicExecutionRole` is NOT (so logging fails). The
   deploy that added VPC access likely detached the basic execution
   role by mistake.

4. **Confirmed the log group does not exist.** `describe-log-groups`
   returns empty — the log group was never created. This rules out
   retention expiry, subscription filter drops, and data protection
   redaction. The diagnosis is narrowed to the very first step of
   ingestion: log-group creation.

5. **Did NOT recommend code changes.** The application code is
   innocent; the execution role is the broken thing. The skill's
   remediation is one IAM attach command, not a code review.

## Slash-command invocation

```
/aws:troubleshoot-cloudwatch-logs-not-ingesting
```

Or via the orchestrator:

```
/aws:pipeline
You: "Lambda function fn-prod-processor has no CloudWatch Logs"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: cloudwatch-logs-not-ingesting-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate ingestion:

```bash
# Confirm the managed policy is attached
aws iam list-attached-role-policies \
  --role-name fn-prod-processor-role \
  --query 'AttachedPolicies[?PolicyName==`AWSLambdaBasicExecutionRole`]' \
  --output json

# Re-invoke the function to trigger log-group auto-creation
aws lambda invoke --function-name fn-prod-processor \
  --payload '{"httpMethod":"GET"}' /tmp/out.json --profile default

# Confirm the log group now exists and has a stream
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/fn-prod-processor
aws logs describe-log-streams --log-group-name /aws/lambda/fn-prod-processor \
  --order-by LastEventTime --descending --limit 1
aws logs get-log-events --log-group-name /aws/lambda/fn-prod-processor \
  --log-stream-name <latest-stream> --limit 10
```

Then monitor the function's log group for 5-10 minutes to confirm
sustained ingestion.
