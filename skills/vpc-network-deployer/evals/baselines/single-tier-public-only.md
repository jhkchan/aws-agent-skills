# Baseline (no-skill) response: single-tier-public-only

This file captures what a generic assistant produces WITHOUT the
vpc-network-deployer skill loaded — the contrast that proves the skill
flags a single-tier public-only VPC as an anti-pattern
(PREREQUISITES_MISSING) instead of proceeding.

---

Here's the deployment plan:

- VPC: 10.99.0.0/24 in ap-southeast-1
- 1 AZ (ap-southeast-1a)
- Public subnet only (10.99.0.0/24)
- Internet Gateway for internet access

Since all your workloads are in the public subnet, they'll have direct
internet access for calling third-party APIs.

Commands:

1. aws ec2 create-vpc --cidr-block 10.99.0.0/24
2. aws ec2 create-subnet --cidr-block 10.99.0.0/24 --availability-zone ap-southeast-1a
3. aws ec2 create-internet-gateway
4. aws ec2 attach-internet-gateway
5. Create route table with 0.0.0.0/0 → IGW

This is a simple setup that should work for your microservice.
