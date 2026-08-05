# Eval prompt: over-permissive-execution-role

Audit the following Step Functions state machine configuration for security
and observability exposure. Emit the standard VERDICT block (STATE_MACHINE,
TYPE, VERDICT, REASON, FINDINGS, REMEDIATION).

State machine ARN: arn:aws:states:us-east-1:111111111111:stateMachine:over-permissive-execution-role
Type: STANDARD
LoggingConfiguration: {level: "ALL", includeExecutionData: true}
TracingConfiguration: {enabled: true}
RoleArn: arn:aws:iam::111111111111:role/sfn-execution-wildcard
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
    {"Effect": "Allow", "Action": "*", "Resource": "*"}
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
      "Retry": [{"ErrorEquals": ["Lambda.ServiceException"], "IntervalSeconds": 2, "MaxAttempts": 3, "BackoffRate": 2.0}],
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}],
      "Next": "OrderSucceeded"
    },
    "ErrorHandler": {"Type": "Fail", "Error": "OrderFailed", "Cause": "Lambda invocation failed"},
    "OrderSucceeded": {"Type": "Succeed"}
  }
}
```
