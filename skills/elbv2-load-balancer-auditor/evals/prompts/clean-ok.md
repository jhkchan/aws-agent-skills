# Eval prompt: clean-ok

Audit the following ELBv2 load balancer configuration for security exposure.
Emit the standard VERDICT block (LB, VERDICT, REASON, FINDINGS, REMEDIATION).

Load balancer ARN: arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/clean-ok/aaa999bbb
Type: application
Scheme: internet-facing
State: active
Security groups: sg-0eee5555
Access logs: enabled (S3 bucket: alb-logs-prod, prefix: prod)
Deletion protection: enabled
WAF: associated (web-acl: waf-prod-acl)

Listeners:
  - Protocol: HTTPS, Port: 443
    SslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
    DefaultAction: forward to tg-prod-web
  - Protocol: HTTP, Port: 80
    DefaultAction: redirect to HTTPS://#{host}:443/#{path}?#{query} (HTTP_301)

Security group sg-0eee5555 inbound rules:
  - TCP 443 from 0.0.0.0/0
  - TCP 80 from 0.0.0.0/0

Target groups:
  - tg-prod-web: 4 registered targets (all healthy)
