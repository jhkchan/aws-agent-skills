# Eval: db-private-cidr

Audit the following EC2 security group for public exposure and compliance violations.

Security Group: db-private-cidr
Inbound rules:
  - Port: 3306
    Protocol: TCP
    Source: 10.0.0.0/8

Expected verdict: RESTRICTED
