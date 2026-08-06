# Eval: all-ports-open

Audit the following EC2 security group for public exposure and compliance violations.

Security Group: all-ports-open
Inbound rules:
  - Port: 0-65535
    Protocol: TCP
    Source: 0.0.0.0/0

Expected verdict: OPEN
