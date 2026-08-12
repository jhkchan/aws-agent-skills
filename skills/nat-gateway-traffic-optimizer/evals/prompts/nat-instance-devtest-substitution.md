# Eval prompt: nat-instance-devtest-substitution

Optimise the following VPC's NAT Gateway cost. Walk the NAT Gateway vs
NAT Instance cost comparison decision framework and emit the standard
optimization block (VPC, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

VPC: vpc-nat-instance-devtest-substitution
Environment: dev (non-production)
Region: us-east-1
NAT Gateways: 1 (us-east-1a)

NAT Monthly Spend:
  - Hourly: 1 × $0.045 × 730 = $32.85
  - Data processing: 30 GB × $0.045 = $1.35
  - Total: $34.20/month

Existing VPC Endpoints: none

VPC Flow Logs (last 7 days, monthly projection):
  - Total traffic: 30 GB (mixed: S3, API calls, package downloads)

Workload context: Dev environment used by 3 developers. EC2
instances in private subnets download packages and run tests.
No production traffic. No availability requirement. If the NAT
Instance is down, developers can wait for a reboot.
