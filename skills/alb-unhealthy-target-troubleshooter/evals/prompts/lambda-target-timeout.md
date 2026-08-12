# Eval prompt: lambda-target-timeout

Diagnose the ALB target health failure for the following target group.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: ALB target group `tg-alb-lambda-target` shows the Lambda target
as unhealthy with TargetHealthReason `Target.FailedHealthChecks`. The
function `fn-alb-processor` is invoked by the ALB for health checks but
times out every time.

```text
TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-alb-lambda-target/mno345
TargetType: lambda
HealthCheckProtocol: HTTP (path and port ignored for Lambda)
Target: arn:aws:lambda:us-east-1:111111111111:function:fn-alb-processor

Lambda function configuration:
  FunctionName: fn-alb-lambda-target
  Runtime: nodejs20.x
  Timeout: 3
  MemorySize: 256
  Handler: index.handler

Recent Lambda logs:
  START RequestId: abc-123 Version: $LATEST
  INFO  Querying database for health status...
  Task timed out after 3.00 seconds
  END RequestId: abc-123 Duration: 3000.00 ms
```

The function's database query takes 5-8 seconds; it was designed for
actual request processing, not fast health checks. The ALB invokes the
function synchronously for each health check, and the 3-second timeout
is too short for the handler to complete.
