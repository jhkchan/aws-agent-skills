# Eval prompt: express-tracing-noop

Audit the following Step Functions state machine configuration for security
and observability exposure. Emit the standard VERDICT block (STATE_MACHINE,
TYPE, VERDICT, REASON, FINDINGS, REMEDIATION).

State machine ARN: arn:aws:states:us-east-1:111111111111:stateMachine:express-tracing-noop
Type: EXPRESS
LoggingConfiguration: {level: "ALL", includeExecutionData: true}
TracingConfiguration: {enabled: true}
RoleArn: arn:aws:iam::111111111111:role/sfn-execution-scoped
Role trust policy:

```json
{
  "Effect": "Allow",
  "Principal": {"Service": "states.amazonaws.com"},
  "Action": "sts:AssumeRole"
}
```

Role identity policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:111111111111:function:quick-handler"
    },
    {
      "Effect": "Allow",
      "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "logs:PutLogEvents", "logs:CreateLogDelivery", "logs:DescribeLogGroups"],
      "Resource": "*"
    }
  ]
}
```

Definition (ASL):

```json
{
  "StartAt": "QuickInvoke",
  "States": {
    "QuickInvoke": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:111111111111:function:quick-handler",
      "TimeoutSeconds": 30,
      "Retry": [{"ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"], "IntervalSeconds": 1, "MaxAttempts": 2, "BackoffRate": 2.0}],
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}],
      "Next": "Done"
    },
    "ErrorHandler": {"Type": "Fail", "Error": "QuickFailed", "Cause": "Unhandled"},
    "Done": {"Type": "Succeed"}
  }
}
```
