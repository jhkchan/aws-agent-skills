# Eval: capacity-reservation-targeting

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — x86_64 AMI + c7i.large, targeted capacity reservation cr-0abc123def456, reservation matches

## Prompt

Create a launch template targeting capacity reservation
cr-0abc123def456 in us-east-1. AMI: ami-0xyz789 (x86_64,
AL2023). Instance type: c7i.large. The reservation
cr-0abc123def456 is active with InstanceType c7i.large,
AvailabilityZone us-east-1a, InstancePlatform Linux/UNIX.
Key pair: prod-key. Security group: sg-0resv123 (VPC
vpc-0abc123def). IAM profile: compute-role. Subnet:
subnet-0usEast1a. IMDSv2 required. Tags: Workload=
reservation-bound. Account: 123456789012.
