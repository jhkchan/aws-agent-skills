# Eval prompt: vpc-cdk-l3-construct

Generate IaC code. Emit the standard VERDICT block (PATTERN, TOOL,
VERDICT, TEMPLATE, VALIDATION, SECURITY, FINDINGS, REMEDIATION).

Pattern: vpc (VPC + public/private subnets + NAT + routes)
Tool: cdk (v2, TypeScript)

Requirements:
- Environment: prod
- CIDR: 10.0.0.0/16
- 3 AZs
- 2 NAT gateways (HA for prod — do not use single NAT)
- Subnet configuration: public, private (PRIVATE_WITH_EGRESS), isolated
- Flow logs: ALL traffic to CloudWatch Logs
- S3 VPC gateway endpoint on the VPC
- DNS hostnames and DNS support enabled
- Tags: Environment, Owner via stack-level tag propagation

Expected: AUTOMATED. The skill emits CDK v2 TypeScript code using the L3
Vpc construct from aws-cdk-lib/aws-ec2, with the correct subnet
configuration, flow logs, and S3 endpoint.
