# Eval: imdsv2-tags-graviton

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — arm64 AMI + m7g.large, IMDSv2 required, tag specs on instance+volume+ENI, gp3 block devices, IPv6 ENI

## Prompt

Create a launch template named "graviton-web-server" in
us-east-1. AMI: ami-0abcdef1234567890 (arm64, AL2023).
Instance type: m7g.large. Key pair: prod-graviton-key.
Security groups: sg-0abc123, sg-0def456 (both in VPC
vpc-0abc123def). IAM instance profile: web-server-role
(role attached). Subnet: subnet-0abc123def456. Public IP:
yes. IPv6: 1 address. IMDSv2 required with hop limit 2
(containerized workload). Block devices: root 30 GB gp3
DeleteOnTermination true, secondary 100 GB gp3 6000 IOPS
DeleteOnTermination true. Tags on instance (Name=
graviton-web-server, Environment=production), volume
(Name=graviton-web-root), network-interface (Name=
graviton-web-eni-0). Account: 123456789012.
