# Eval prompt: nat-gateway-no-gateway-endpoints

Optimize the AWS account data transfer costs. Walk the seven-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Account: 123456789012 (case nat-gateway-no-gateway-endpoints)
Region: us-east-1 primary
Monthly data transfer costs (Cost Explorer, last 30 days):
  - NatGateway-Bytes: 12,000 GB × $0.045 = $540
  - NatGateway hourly: 3 NAT × $0.045/h × 730h = $98.55
  - DataTransfer-Regional-Bytes: 1,000 GB × $0.02 = $20
  - DataTransfer-Out-Bytes: 800 GB × $0.09 = $72
VPC topology:
  - VPC-A in us-east-1 (3 AZs; primary app)
  - 3 NAT Gateways (one per AZ for HA)
  - VPC Endpoints: NONE
Workload context: microservices in private subnets pulling from S3
(~95% of NAT traffic) and DynamoDB (~3%). General internet egress
is minimal.
