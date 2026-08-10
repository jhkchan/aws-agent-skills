# Eval prompt: already-optimal-data-transfer

Optimize the AWS account data transfer costs. Walk the seven-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Account: 123456789016 (case already-optimal-data-transfer)
Region: us-east-1 primary; us-west-2 secondary
Monthly data transfer costs (Cost Explorer, last 30 days):
  - NatGateway-Bytes: minimal (only general internet egress from
    dev/test VPC; $15/month)
  - DataTransfer-Regional-Bytes: minimal (workers AZ-pinned;
    $25/month)
  - DataTransfer-Out-Bytes: minimal (CloudFront handles S3 egress
    to viewers; $50/month on EC2 direct egress for on-prem sync
    via DX)
  - Cross-region: Aurora Global Database only (DR-justified;
    priced via Aurora storage)
  - TransitGateway-Bytes: none (peering used)
  - RDS-DataTransfer: none (Aurora)
  - Direct Connect: 1Gbps port $220/month + 5,000GB × $0.02
    = $100/month outbound
VPC topology:
  - 3 VPCs in us-east-1 (VPC peering, full mesh, free)
  - 1 VPC in us-west-2 (Aurora Global DB from us-east-1)
  - VPC Gateway Endpoints: S3 + DynamoDB in all VPCs with private
    subnets
  - VPC Interface Endpoints: SQS in 2 VPCs (above break-even)
  - Workers AZ-pinned to Aurora readers per VPC
  - Aurora Multi-AZ (storage-layer replication, free)
  - Direct Connect 1Gbps to on-prem data center (above break-even
    at 5TB/month sync)
Workload context: multi-region SaaS with active-active Aurora Global
Database for DR, CloudFront for global S3 content, on-prem sync for
hybrid analytics.
