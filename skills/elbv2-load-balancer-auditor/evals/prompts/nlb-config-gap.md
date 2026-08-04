# Eval prompt: nlb-config-gap

Audit the following ELBv2 load balancer configuration for security exposure.
Emit the standard VERDICT block (LB, VERDICT, REASON, FINDINGS, REMEDIATION).

Load balancer ARN: arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/net/nlb-config-gap/vwx345yz
Type: network
Scheme: internet-facing
State: active
Access logs: enabled (S3 bucket: nlb-logs-prod, prefix: tcp)
Cross-zone load balancing: disabled
Deletion protection: disabled

Listeners:
  - Protocol: TCP, Port: 443
    SslPolicy: (none — TCP passthrough, no TLS termination)
    DefaultAction: forward to tg-nlb-prod

Target groups:
  - tg-nlb-prod: 2 registered targets (all healthy)
