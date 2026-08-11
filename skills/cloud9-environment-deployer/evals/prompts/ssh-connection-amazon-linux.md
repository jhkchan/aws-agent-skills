# Eval: ssh-connection-amazon-linux

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CONNECT_SSH mode, Amazon Linux 2, key pair required, port 22 from trusted CIDR, 60-min auto-hibernate

## Prompt

Create a Cloud9 environment named legacy-ide in us-east-1. t3.large
instance, Amazon Linux 2, SSH connection mode. Subnet
subnet-public111. Security group sg-cloud9-ssh with port 22 from
10.0.0.0/8. Key pair my-cloud9-key. Instance profile
Cloud9SSHProfile. Auto-hibernate at 60 minutes. Tags:
Environment=staging, Team=ops.
