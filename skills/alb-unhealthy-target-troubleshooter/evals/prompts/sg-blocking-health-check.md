# Eval prompt: sg-blocking-health-check

Diagnose the ALB target health failure for the following target group.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: ALB target group `tg-alb-sg-blocking` shows all 4 targets as
unhealthy with TargetHealthReason `Target.ConnectionFailed`. The ALB
was recently migrated to new subnets in a different CIDR
(172.16.0.0/16). The target security group was not updated.

```text
TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/tg-alb-sg-blocking/def456
TargetType: ip
HealthCheckPath: /api/health
HealthCheckProtocol: HTTPS
HealthCheckPort: 443
Matcher: { HttpCode: "200" }
Target Port: 443
Protocol: HTTPS
Targets: 4 registered, 4 unhealthy (all Reason: Target.ConnectionFailed)

Target SG (sg-app-443) ingress rules:
  - port 443, source 10.0.0.0/8
  - port 22, source 10.0.0.0/8

ALB details:
  - ALB security group: sg-alb
  - ALB subnets: subnet-172a, subnet-172b (CIDR 172.16.1.0/24, 172.16.2.0/24)
  - ALB ENI IPs: 172.16.1.15, 172.16.1.23, 172.16.2.10, 172.16.2.18

Direct curl from within the target subnet (10.0.1.0/24) to a
target on port 443 returns 200 (app works locally).
```

The target SG allows 10.0.0.0/8 but the ALB nodes are in 172.16.x.x
after the subnet migration. The SG was not updated to reference the
ALB security group.
