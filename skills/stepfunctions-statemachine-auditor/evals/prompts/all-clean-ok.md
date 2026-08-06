# Eval prompt: all-clean-ok

Audit the following Step Functions state machine configuration for security
and observability exposure. Emit the standard VERDICT block (STATE_MACHINE,
TYPE, VERDICT, REASON, FINDINGS, REMEDIATION).

State machine ARN: arn:aws:states:us-east-1:111111111111:stateMachine:all-clean-ok
Type: STANDARD
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
      "Resource": "arn:aws:lambda:us-east-1:111111111111:function:order-processor"
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
  "StartAt": "ProcessOrder",
  "States": {
    "ProcessOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:111111111111:function:order-processor",
      "TimeoutSeconds": 30,
      "Retry": [{"ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"], "IntervalSeconds": 2, "MaxAttempts": 3, "BackoffRate": 2.0}],
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}],
      "Next": "OrderSucceeded"
    },
    "ErrorHandler": {"Type": "Fail", "Error": "OrderFailed", "Cause": "Unhandled error"},
    "OrderSucceeded": {"Type": "Succeed"}
  }
}
```
