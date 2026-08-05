# Eval prompt: missing-error-handling-config-gap

Audit the following Step Functions state machine configuration for security
and observability exposure. Emit the standard VERDICT block (STATE_MACHINE,
TYPE, VERDICT, REASON, FINDINGS, REMEDIATION).

State machine ARN: arn:aws:states:us-east-1:111111111111:stateMachine:missing-error-handling-config-gap
Type: STANDARD
LoggingConfiguration: {level: "ALL", includeExecutionData: true}
TracingConfiguration: {enabled: true}
RoleArn: arn:aws:iam::111111111111:role/sfn-execution-scoped
Role identity policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:111111111111:function:risky-handler"
    },
    {
      "Effect": "Allow",
      "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "logs:PutLogEvents", "logs:CreateLogDelivery"],
      "Resource": "*"
    }
  ]
}
```

Definition (ASL):

```json
{
  "StartAt": "InvokeRisky",
  "States": {
    "InvokeRisky": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:111111111111:function:risky-handler",
      "Next": "Done"
    },
    "Done": {"Type": "Succeed"}
  }
}
```
