# Eval prompt: port-mismatch-health-check

Diagnose the ALB target health failure for the following target group.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: ALB target group `tg-alb-port-mismatch` shows all 3 targets as
unhealthy with TargetHealthReason `Target.ConnectionFailed`. The targets
are EC2 instances running on port 8080, but the health check port was
set to 80.

```text
TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-alb-port-mismatch/jkl012
TargetType: instance
HealthCheckPath: /healthz
HealthCheckPort: 80
HealthCheckProtocol: HTTP
Matcher: { HttpCode: "200" }
Target Port: 8080
Protocol: HTTP
Targets: 3 registered, 3 unhealthy (all Reason: Target.ConnectionFailed)

Application context:
  - Application listens on port 8080 (confirmed via ss -tlnp)
  - Nothing listens on port 80

Target SG allows inbound from sg-alb on BOTH port 80 and 8080.

Direct curl from bastion:
  curl http://10.0.1.50:8080/healthz → 200 OK
  curl http://10.0.1.50:80/healthz → connection refused
```

The health check port overrides the target's registered port. Even
though the target is registered on 8080 and the SG allows both ports,
the health check is probing port 80 where nothing listens.
