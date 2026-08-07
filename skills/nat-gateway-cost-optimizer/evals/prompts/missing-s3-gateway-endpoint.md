# Eval prompt: missing-s3-gateway-endpoint

Optimise the NAT Gateway cost for the VPC below. Walk the four-dimension
analysis (Gateway endpoints, Interface endpoints, topology, NAT Instance)
and emit the standard optimisation block (VPC, VERDICT, REASON,
RECOMMENDATION, SAVINGS, IMPLEMENTATION).

VPC: vpc-missing-s3-gateway-endpoint
Region: us-east-1
Environment: production

NAT Gateways: 3 (one per AZ — us-east-1a, 1b, 1c), all available
Current VPC Endpoints: none

Data processing (Cost Explorer, last 30 days):
  - NAT Gateway data processing: 2,400 GB total ($108.00)
  - NAT Gateway base: 3 × $32.85 = $98.55
  - Total NAT cost: $206.55 (Cost Explorer shows $140.85 after discounts)

Traffic breakdown (VPC Flow Logs, last 7 days, monthly projection):
  - S3: 900 GB/month
  - DynamoDB: 200 GB/month
  - ECR: 150 GB/month
  - Other AWS services (SSM, STS, etc.): 150 GB/month
  - Internet (non-AWS): 1,000 GB/month

Workload context: EKS production cluster with multiple microservices
pulling container images from ECR and reading/writing S3 and DynamoDB.
High-throughput, requires multi-AZ HA.
