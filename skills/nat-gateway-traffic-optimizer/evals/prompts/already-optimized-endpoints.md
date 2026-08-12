# Eval prompt: already-optimized-endpoints

Optimise the following VPC's NAT Gateway cost. Walk all optimization
dimensions (gateway-endpoint, interface-endpoint, topology,
nat-instance, routing, cloudfront) and emit the standard optimization
block (VPC, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

VPC: vpc-already-optimized-endpoints
Environment: production
Region: us-east-1
NAT Gateways: 2 (us-east-1a, us-east-1b)

NAT Monthly Spend:
  - Hourly: 2 × $0.045 × 730 = $65.70
  - Data processing: 500 GB × $0.045 = $22.50
  - Total: $88.20/month

Existing VPC Endpoints:
  - S3 Gateway Endpoint (active)
  - DynamoDB Gateway Endpoint (active)
  - ECR Interface Endpoint api + dkr (active, 3-AZ)

VPC Flow Logs (last 7 days, monthly projection):
  - S3 traffic: 0 GB (through Gateway Endpoint)
  - DynamoDB traffic: 0 GB (through Gateway Endpoint)
  - ECR traffic: 0 GB (through Interface Endpoint)
  - Remaining through NAT: 500 GB (third-party APIs, downloads)

Workload context: Production multi-AZ VPC. S3, DynamoDB, and ECR
traffic already routed through VPC endpoints. Remaining NAT
traffic is to third-party APIs and internet downloads that cannot
be eliminated by endpoints.
