# Eval: web-tier-https

Audit the following EC2 security group for public exposure and compliance violations.

Security Group: web-tier-https
Inbound rules:
  - Port: 443
    Protocol: TCP
    Source: 0.0.0.0/0
  - Port: 22
    Protocol: TCP
    Source: 10.0.0.0/8

Expected verdict: PUBLIC_NONCRITICAL
