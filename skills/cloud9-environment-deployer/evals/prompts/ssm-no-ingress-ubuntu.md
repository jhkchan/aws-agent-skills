# Eval: ssm-no-ingress-ubuntu

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CONNECT_SSM mode, Ubuntu platform, no inbound SG rules, AmazonSSMManagedInstanceCore in instance profile, 30-min auto-hibernate

## Prompt

Create a Cloud9 environment named dev-team-ide in us-east-1.
t3.medium instance, Ubuntu platform, SSM connection mode (no
ingress). Subnet subnet-aaa11122. Security group sg-cloud9-ssm
with no inbound rules. Instance profile Cloud9InstanceProfile
with AmazonSSMManagedInstanceCore. Auto-hibernate at 30 minutes.
Tags: Environment=production, Team=dev.
