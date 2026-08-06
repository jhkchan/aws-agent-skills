# Eval: db-mysql-open

Audit the following EC2 security group for public exposure and compliance violations.

Security Group: db-mysql-open
Inbound rules:
  - Port: 3306
    Protocol: TCP
    Source: 0.0.0.0/0

