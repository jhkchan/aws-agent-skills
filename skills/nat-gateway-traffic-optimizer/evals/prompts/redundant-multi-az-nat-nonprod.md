# Eval prompt: redundant-multi-az-nat-nonprod

Optimise the following VPC's NAT Gateway cost. Walk the topology
consolidation (single vs multi-AZ NAT Gateway) decision framework and
emit the standard optimization block (VPC, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

VPC: vpc-redundant-multi-az-nat-nonprod
Environment: staging (non-production)
Region: us-east-1
NAT Gateways: 3 (us-east-1a, us-east-1b, us-east-1c)

NAT Monthly Spend:
  - Hourly: 3 × $0.045 × 730 = $98.55
  - Data processing: 200 GB × $0.045 = $9.00
  - Total: $107.55/month

Existing VPC Endpoints: S3 Gateway Endpoint (already created)

VPC Flow Logs (last 7 days, monthly projection):
  - S3 traffic: 0 GB (already through Gateway Endpoint)
  - DynamoDB traffic: 20 GB
  - Other: 180 GB

Workload context: Staging environment for QA testing. No 24/7
availability requirement. Single-AZ egress failure is tolerable
(staging can be down for short periods during AZ outages).
