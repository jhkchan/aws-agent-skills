# Eval prompt: flow-logs-not-enabled

Optimise the following VPC's NAT Gateway cost. Walk the traffic
analysis decision framework and emit the standard optimization block
(VPC, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

VPC: vpc-flow-logs-not-enabled
Environment: production
Region: us-east-1
NAT Gateways: 2 (us-east-1a, us-east-1b)

NAT Monthly Spend (from Cost Explorer):
  - Hourly: 2 × $0.045 × 730 = $65.70
  - Data processing: 600 GB × $0.045 = $27.00
  - Total: $92.70/month

VPC Flow Logs: NOT ENABLED

Existing VPC Endpoints: none

Workload context: Recently inherited from another team. No
documentation on what traffic flows through the NAT Gateways.
Cannot determine which AWS services are being accessed without
per-service traffic breakdown.
