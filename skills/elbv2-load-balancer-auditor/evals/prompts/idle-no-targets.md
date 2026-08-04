# Eval prompt: idle-no-targets

Audit the following ELBv2 load balancer configuration for security exposure.
Emit the standard VERDICT block (LB, VERDICT, REASON, FINDINGS, REMEDIATION).

Load balancer ARN: arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/idle-no-targets/pqr012stu
Type: application
Scheme: internal
State: active
Security groups: sg-0ddd4444
Access logs: enabled (S3 bucket: alb-logs-prod, prefix: legacy)
Deletion protection: enabled

Listeners:
  - Protocol: HTTPS, Port: 443
    SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
    DefaultAction: forward to tg-legacy-app

Security group sg-0ddd4444 inbound rules:
  - TCP 443 from 10.0.0.0/8

Target groups:
  - tg-legacy-app: 0 registered targets
