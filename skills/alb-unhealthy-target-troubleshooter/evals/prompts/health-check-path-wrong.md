# Eval prompt: health-check-path-wrong

Diagnose the ALB target health failure for the following target group.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: ALB target group `tg-alb-health-check-path` shows all 6 targets
as unhealthy. TargetHealthReason is `Target.FailedHealthChecks`. The
application was redeployed last night and the health endpoint changed
from `/health` to `/healthz`. The target group configuration was not
updated.

```text
TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-alb-health-check-path/abc123
TargetType: instance
HealthCheckPath: /health
HealthCheckPort: traffic-port
HealthCheckProtocol: HTTP
Matcher: { HttpCode: "200" }
Target Port: 8080
Protocol: HTTP
Targets: 6 registered, 6 unhealthy (all Reason: Target.FailedHealthChecks)

Direct curl from a bastion host in the same VPC:
  curl -s -o /dev/null -w "%{http_code}" http://10.0.1.42:8080/health
  → 404
  curl -s -o /dev/null -w "%{http_code}" http://10.0.1.42:8080/healthz
  → 200

Security group sg-app allows inbound from sg-alb on port 8080.
```

The health check path is the likely culprit — the application moved
its health endpoint but the target group still points at the old path.
