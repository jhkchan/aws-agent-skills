# Eval prompt: ha-multi-az-three-tier

Design a deployment plan for a production VPC. Emit the standard VERDICT
block (VPC_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

Requirements:

- Region: us-east-1
- AZ count: 3 (us-east-1a, us-east-1b, us-east-1c)
- CIDR: 10.0.0.0/16 (RFC 1918, verified no overlap with existing VPCs or
  on-premises ranges)
- Tiers: public, private, database
- NAT strategy: HA (one NAT Gateway per AZ)
- VPC Endpoints: S3, DynamoDB (Gateway), Secrets Manager, SSM, KMS
  (Interface)
- Flow Logs: all-traffic to S3, 1-year retention
- Security Groups: reference by name, least-privilege
- DNS: enableDnsHostnames + enableDnsSupport
- IPv6: dual-stack

Existing-VPC context: two existing VPCs in the account use 10.10.0.0/16
and 10.20.0.0/16. No Direct Connect or Site-to-Site VPN.
