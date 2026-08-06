# Eval: bastion-ssh-open

Audit the following EC2 security group for public exposure and compliance violations.

Security Group: bastion-ssh-open
Inbound rules:
  - Port: 22
    Protocol: TCP
    Source: 0.0.0.0/0

Expected verdict: OPEN
