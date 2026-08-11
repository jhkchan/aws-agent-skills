# Eval: network-interface-public-ip-ipv6

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — x86_64 + c7i.xlarge, ENI DeviceIndex 0 with AssociatePublicIpAddress true + Ipv6AddressCount 1, gp3 root

## Prompt

Create a launch template for a public-facing API server in
us-east-1. AMI: ami-0apiimage (x86_64). Instance type:
c7i.xlarge. The instance needs a public IP and one IPv6
address on its primary ENI. Subnet: subnet-0public (has IPv6
CIDR). Security group: sg-0api (VPC vpc-0public). Key pair:
api-key. IAM profile: api-role. IMDSv2 required. Block
device: root 30 GB gp3 DeleteOnTermination true. Tags:
Name=api-server, Tier=public. Account: 123456789012.
