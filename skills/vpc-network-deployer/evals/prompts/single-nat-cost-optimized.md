# Eval prompt: single-nat-cost-optimized

Design a deployment plan for a staging VPC. Emit the standard VERDICT
block (VPC_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

Requirements:

- Region: us-west-2
- AZ count: 2 (us-west-2a, us-west-2b)
- CIDR: 10.50.0.0/16 (RFC 1918, verified no overlap with existing VPCs)
- Tiers: public, private (no database tier required for staging)
- NAT strategy: cost-optimized (single NAT Gateway in AZ-a to keep
  staging cost low)
- VPC Endpoints: S3, DynamoDB (Gateway only — keep endpoint cost low)
- Flow Logs: all-traffic to S3, 90-day retention
- Security Groups: reference by name, least-privilege
- DNS: enableDnsHostnames + enableDnsSupport
