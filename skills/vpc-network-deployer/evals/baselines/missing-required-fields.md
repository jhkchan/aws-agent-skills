# Baseline (no-skill) response: missing-required-fields

This file captures what a generic assistant produces WITHOUT the
vpc-network-deployer skill loaded — the contrast that proves the skill
identifies missing required fields (region, CIDR) and emits
PREREQUISITES_MISSING instead of guessing values.

---

I'd be happy to help design your VPC. I'll assume the following defaults
since they weren't specified:

- Region: us-east-1
- CIDR: 10.0.0.0/16

Here's the plan:

- VPC: 10.0.0.0/16 in us-east-1
- 3 AZs with public, private, and database tiers
- HA NAT Gateways (one per AZ)

Commands:

1. aws ec2 create-vpc --cidr-block 10.0.0.0/16
2. Create subnets across 3 AZs
3. Create and attach Internet Gateway
4. Create NAT Gateways
5. Set up route tables and security groups

Let me know if you'd like to adjust the region or CIDR.
