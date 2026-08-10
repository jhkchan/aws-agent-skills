# Eval prompt: tgw-versus-peering-small-fleet

Optimize the AWS account data transfer costs. Walk the seven-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Account: 123456789014 (case tgw-versus-peering-small-fleet)
Region: us-east-1
Monthly data transfer costs (Cost Explorer, last 30 days):
  - TransitGateway-Bytes: 5,000 GB × $0.04 (round-trip) = $200
  - TransitGateway hourly: 3 attachments × $0.05/h × 730h = $109.50
  - Total TGW cost: $309.50/month
VPC topology:
  - VPC-A, VPC-B, VPC-C in us-east-1 (all intra-region)
  - Transit Gateway connecting all 3
  - Full mesh traffic pattern: each VPC exchanges ~500GB/month
    with each other VPC
Workload context: microservices in each VPC calling APIs in the
others; no centralized egress or inspection requirement.
