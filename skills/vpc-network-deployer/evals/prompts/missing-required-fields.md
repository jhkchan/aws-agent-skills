# Eval prompt: missing-required-fields

Design a deployment plan for a VPC. Emit the standard VERDICT block
(VPC_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- AZ count: 3
- Tiers: public, private, database
- NAT strategy: HA (one NAT Gateway per AZ)
- VPC Endpoints: S3, DynamoDB (Gateway)
- Flow Logs: all-traffic to CloudWatch Logs

The caller has not specified the AWS region or the CIDR block for the
VPC.
