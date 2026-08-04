# Eval prompt: insecure-listener-tls10

Audit the following ELBv2 load balancer configuration for security exposure.
Emit the standard VERDICT block (LB, VERDICT, REASON, FINDINGS, REMEDIATION).

Load balancer ARN: arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/insecure-listener-tls10/abc123def
Type: application
Scheme: internet-facing
State: active
Security groups: sg-0aaa1111
Access logs: enabled (S3 bucket: alb-logs-prod, prefix: web)
Deletion protection: enabled
Cross-zone load balancing: enabled (always on for ALB)

Listeners:
  - Protocol: HTTPS, Port: 443
    SslPolicy: ELBSecurityPolicy-TLS-1.0-2015-04
    DefaultAction: forward to tg-web-prod

Security group sg-0aaa1111 inbound rules:
  - TCP 443 from 0.0.0.0/0

Target groups:
  - tg-web-prod: 3 registered targets (all healthy)
