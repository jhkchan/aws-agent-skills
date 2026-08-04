# Eval prompt: no-access-logs-internal

Audit the following ELBv2 load balancer configuration for security exposure.
Emit the standard VERDICT block (LB, VERDICT, REASON, FINDINGS, REMEDIATION).

Load balancer ARN: arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/no-access-logs-internal/jkl789mno
Type: application
Scheme: internal
State: active
Security groups: sg-0ccc3333
Access logs: disabled
Deletion protection: enabled

Listeners:
  - Protocol: HTTPS, Port: 443
    SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
    DefaultAction: forward to tg-internal-svc

Security group sg-0ccc3333 inbound rules:
  - TCP 443 from 10.0.0.0/8

Target groups:
  - tg-internal-svc: 2 registered targets (all healthy)
