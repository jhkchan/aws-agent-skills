# Eval prompt: redundant-multi-az-nat-nonprod

Optimise the NAT Gateway cost for the VPC below. Walk the four-dimension
analysis and emit the standard optimisation block (VPC, VERDICT, REASON,
RECOMMENDATION, SAVINGS, IMPLEMENTATION).

VPC: vpc-redundant-multi-az-nat-nonprod
Region: us-east-1
Environment: staging

NAT Gateways: 2 (us-east-1a, 1b), both available
Current VPC Endpoints: none

Data processing (Cost Explorer, last 30 days):
  - NAT Gateway data processing: 80 GB total ($3.60)
  - NAT Gateway base: 2 × $32.85 = $65.70
  - Total NAT cost: $69.20

Traffic breakdown (VPC Flow Logs, last 7 days, monthly projection):
  - S3: 40 GB/month
  - Other AWS services: 10 GB/month
  - Internet: 30 GB/month
Cross-AZ traffic: < 30 GB/month

Workload context: staging environment for QA testing; no HA requirement;
runs during business hours only.
