# Eval prompt: deregistration-delay-stranding

Diagnose the ALB target health state for the following target group.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: ALB target group `tg-alb-deregistration` shows 3 targets in
state `draining`. The ASG performed an instance refresh 10 minutes
ago. The draining targets have not transitioned to removed yet.
Operators are concerned the targets are stuck.

```text
TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-alb-deregistration/ghi789
TargetType: instance
Targets:
  - i-aaa1: state healthy
  - i-aaa2: state healthy
  - i-bbb1: state draining (deregistered 10 minutes ago)
  - i-bbb2: state draining (deregistered 10 minutes ago)
  - i-bbb3: state draining (deregistered 10 minutes ago)

Target group attributes:
  deregistration_delay.timeout_seconds = 600

No targets show unhealthy or Target.FailedHealthChecks.
All draining targets were healthy before deregistration.
```

The targets are in draining state after an ASG instance refresh. The
deregistration delay is configured to 600 seconds (10 minutes). This is
not a health check failure — the targets are completing in-flight
requests during the configured drain window.
