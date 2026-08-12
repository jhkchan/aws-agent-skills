# Eval prompt: iam-putlogevents-missing-lambda-role

Diagnose the CloudWatch Logs not-ingesting scenario for the following
Lambda function. Walk the symptom-driven diagnostic tree and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `fn-iam-putlogevents-missing-lambda-role` runs successfully
(returns 200 to API Gateway) but no logs appear in CloudWatch. The
expected log group `/aws/lambda/fn-iam-putlogevents-missing-lambda-role`
does not exist. The function was deployed 1 hour ago.

```text
LogGroup (expected): /aws/lambda/fn-iam-putlogevents-missing-lambda-role
Source: Lambda (auto-publishes to /aws/lambda/<name>)
Execution role: arn:aws:iam::111111111111:role/fn-role
Attached policies:
  - AWSLambdaVPCAccessExecutionRole
  - inline: { app-access: { Effect: Allow, Action: [s3:GetObject], Resource: "*" } }

aws iam simulate-principal-policy for the role:
  logs:CreateLogGroup on arn:aws:logs:us-east-1:111111111111:log-group:*: IMPLICIT_DENY
  logs:CreateLogStream on same pattern: IMPLICIT_DENY
  logs:PutLogEvents on same pattern: IMPLICIT_DENY

aws logs describe-log-groups:
  logGroups: [] (log group does not exist)

CloudWatch metrics (last hour):
  AWS/Lambda Invocations: 47
  AWS/Lambda Errors: 0
```

Lambda auto-creates `/aws/lambda/<name>` on the first invocation only
if the execution role allows `logs:CreateLogGroup`. If the role lacks
it, the creation silently fails and subsequent invocations continue to
drop logs. `AWSLambdaBasicExecutionRole` includes all four required
`logs:*` actions; detaching it is the most common cause of missing
Lambda logs.
