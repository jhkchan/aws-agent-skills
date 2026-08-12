# Eval prompt: target-lambda-permission-missing

Diagnose the EventBridge rule failure for the following rule and target.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: PutEvents returns 200; `test-event-pattern` returns
`{"Result": true}`; CloudTrail shows EventBridge attempting to invoke
the Lambda. But the Lambda's CloudWatch logs show zero invocations.

```text
EventBusName: custom.orders-bus
RuleName: ev-target-lambda-permission-missing
EventPattern:
  source: ["myapp.orders"]
  detail-type: ["OrderCreated"]
State: ENABLED

Target Lambda: fn-ev-target-permission (same account)

aws lambda get-policy on fn-ev-target-permission returns:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "APIGatewayInvoke",
      "Effect": "Allow",
      "Principal": {"Service": "apigateway.amazonaws.com"},
      "Action": "lambda:InvokeFunction"
    }
  ]
}
Note: No statement for events.amazonaws.com.

CloudTrail shows EventBridge invocation returning AccessDenied for
  the Lambda ARN.
```

The pattern matches (`test-event-pattern: true`), the rule is ENABLED,
and the bus is correct. The issue is on the target side. Examine the
Lambda resource-based policy for the EventBridge service principal.
