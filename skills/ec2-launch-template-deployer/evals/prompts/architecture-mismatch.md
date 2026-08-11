# Eval: architecture-mismatch

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — x86_64 AMI paired with m7g.large (arm64); template would create but instance would fail to boot

## Prompt

Create a launch template named "web-server" in us-east-1.
AMI: ami-0x86image (x86_64, Amazon Linux 2023). Instance
type: m7g.large (Graviton). Key pair: web-key. Security
group: sg-0web (VPC vpc-0web). IAM profile: web-role.
Subnet: subnet-0web. IMDSv2 required. Tags: Name=web-server.
Account: 123456789012.
