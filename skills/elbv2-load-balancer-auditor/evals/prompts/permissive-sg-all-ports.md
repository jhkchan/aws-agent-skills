# Eval prompt: permissive-sg-all-ports

Audit the following ELBv2 load balancer configuration for security exposure.
Emit the standard VERDICT block (LB, VERDICT, REASON, FINDINGS, REMEDIATION).

Load balancer ARN: arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/permissive-sg-all-ports/def456ghi
Type: application
Scheme: internet-facing
State: active
Security groups: sg-0bbb2222
Access logs: enabled (S3 bucket: alb-logs-prod, prefix: api)
Deletion protection: enabled

Listeners:
  - Protocol: HTTPS, Port: 443
    SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
    DefaultAction: forward to tg-api-prod

Security group sg-0bbb2222 inbound rules:
  - TCP 0-65535 from 0.0.0.0/0
  - TCP 0-65535 from ::/0

Target groups:
  - tg-api-prod: 2 registered targets (all healthy)
