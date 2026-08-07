# Baseline (no-skill) response: cidr-overlap-with-onprem

This file captures what a generic assistant produces WITHOUT the
vpc-network-deployer skill loaded — the contrast that proves the skill
flags CIDR overlap as a hard blocker (PREREQUISITES_MISSING) instead of
proceeding with a broken deployment.

---

Here's the deployment plan for your production VPC:

- VPC CIDR: 10.0.0.0/16
- Region: us-east-1
- 3 AZs with public, private, and database tiers
- HA NAT Gateways (one per AZ)

Since you need connectivity to your on-premises database servers, the
Direct Connect and Site-to-Site VPN will route traffic between the VPC
and the datacenter.

Commands:

1. aws ec2 create-vpc --cidr-block 10.0.0.0/16
2. Create subnets across 3 AZs
3. Create and attach Internet Gateway
4. Create NAT Gateways in each AZ
5. Configure route tables

Let me know if you'd like me to also set up the Direct Connect
configuration.
