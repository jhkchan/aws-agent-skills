# Eval prompt: nat-instance-devtest-substitution

Optimise the NAT Gateway cost for the VPC below. Walk the four-dimension
analysis and emit the standard optimisation block (VPC, VERDICT, REASON,
RECOMMENDATION, SAVINGS, IMPLEMENTATION). Consider whether a NAT Instance
is appropriate for this environment.

VPC: vpc-nat-instance-devtest-substitution
Region: us-east-1
Environment: dev

NAT Gateways: 1 (us-east-1a), available
Current VPC Endpoints: none

Data processing (Cost Explorer, last 30 days):
  - NAT Gateway data processing: 2,000 GB total ($90.00)
  - NAT Gateway base: 1 × $32.85 = $32.85
  - Total NAT cost: $122.85

Traffic breakdown (VPC Flow Logs, last 7 days, monthly projection):
  - S3: 1,500 GB/month (large dataset pulls)
  - Other AWS services: 100 GB/month
  - Internet: 400 GB/month

Workload context: single developer build agent running CI jobs; no HA
requirement; tolerate downtime; runs in a single AZ.
