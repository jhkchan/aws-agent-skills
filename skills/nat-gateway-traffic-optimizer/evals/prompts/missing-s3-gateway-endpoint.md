# Eval prompt: missing-s3-gateway-endpoint

Optimise the following VPC's NAT Gateway cost. Walk the VPC endpoint
and traffic analysis decision framework and emit the standard
optimization block (VPC, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

VPC: vpc-missing-s3-gateway-endpoint
Environment: production
Region: us-east-1
NAT Gateways: 2 (us-east-1a, us-east-1b)

NAT Monthly Spend:
  - Hourly: 2 × $0.045 × 730 = $65.70
  - Data processing: 800 GB × $0.045 = $36.00
  - Total: $101.70/month

Existing VPC Endpoints: none

VPC Flow Logs (last 7 days, monthly projection):
  - S3 traffic: 300 GB (37.5% of total)
  - DynamoDB traffic: 50 GB (6.25% of total)
  - ECR traffic: 100 GB (12.5% of total)
  - SSM traffic: 30 GB (3.75% of total)
  - Other: 320 GB (40% of total)

Workload context: Production multi-AZ VPC serving a web application.
EC2 fleet in private subnets reads from S3 (config files, assets)
and DynamoDB (session data). Multi-AZ NAT required for HA.
