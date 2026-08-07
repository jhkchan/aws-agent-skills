# Baseline (no-skill) response: ha-multi-az-three-tier

This file captures what a generic assistant produces WITHOUT the
vpc-network-deployer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated CHECKLIST, specific
DEPLOY_COMMANDS, expert knowledge of NAT topology cost trade-offs and
route-table design).

---

Here's a plan for your VPC. I'll create a VPC with the CIDR 10.0.0.0/16
in us-east-1 with 3 availability zones. You'll have public, private, and
database subnets across all 3 AZs.

I'll set up NAT Gateways in each AZ for high availability. You'll also
get VPC endpoints for S3 and DynamoDB plus Secrets Manager, SSM, and KMS.

The architecture will look like:

- VPC: 10.0.0.0/16
- Public subnets: 10.0.0.0/24, 10.0.1.0/24, 10.0.2.0/24
- Private subnets: 10.0.3.0/24, 10.0.4.0/24, 10.0.5.0/24
- Database subnets: 10.0.6.0/24, 10.0.7.0/24, 10.0.8.0/24

Commands to deploy:

1. aws ec2 create-vpc --cidr-block 10.0.0.0/16
2. Create subnets in each AZ
3. Create an Internet Gateway and attach it
4. Create NAT Gateways
5. Create route tables and add routes
6. Create security groups
7. Set up VPC endpoints
8. Enable flow logs

This should cover everything you need for a production setup.
