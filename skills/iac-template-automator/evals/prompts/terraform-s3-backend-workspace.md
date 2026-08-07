# Eval prompt: terraform-s3-backend-workspace

Generate a Terraform module. Emit the standard VERDICT block (PATTERN,
TOOL, VERDICT, TEMPLATE, VALIDATION, SECURITY, FINDINGS, REMEDIATION).

Pattern: vpc
Tool: terraform (>= 1.5.0)

Requirements:
- AWS provider: source = "hashicorp/aws", version = "~> 5.0"
- S3 backend with DynamoDB lock table, encrypt = true
- default_tags on the provider block: Environment, Owner, ManagedBy=terraform
- Use the terraform-aws-modules/vpc/aws module (version ~> 5.0)
- Region: us-east-1
- Environment: prod
- CIDR: 10.0.0.0/16
- 3 AZs
- enable_nat_gateway = true for prod
- single_nat_gateway = false for prod
- enable_flow_log = true with CloudWatch Logs

Expected: AUTOMATED. The skill emits a complete Terraform configuration
with pinned AWS provider v5, S3 backend with DynamoDB lock, default_tags,
and the community VPC module invocation.
