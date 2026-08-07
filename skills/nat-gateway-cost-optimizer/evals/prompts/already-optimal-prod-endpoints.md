# Eval prompt: already-optimal-prod-endpoints

Optimise the NAT Gateway cost for the VPC below. Walk the four-dimension
analysis and emit the standard optimisation block (VPC, VERDICT, REASON,
RECOMMENDATION, SAVINGS, IMPLEMENTATION).

VPC: vpc-already-optimal-prod-endpoints
Region: us-east-1
Environment: production

NAT Gateways: 3 (one per AZ), all available
Current VPC Endpoints:
  - S3 Gateway endpoint (com.amazonaws.us-east-1.s3), route tables rtb-a, rtb-b, rtb-c
  - DynamoDB Gateway endpoint (com.amazonaws.us-east-1.dynamodb), route tables rtb-a, rtb-b, rtb-c
  - ECR API Interface endpoint (com.amazonaws.us-east-1.ecr.api), subnets subnet-a, subnet-b, subnet-c
  - ECR Docker Interface endpoint (com.amazonaws.us-east-1.ecr.dkr), subnets subnet-a, subnet-b, subnet-c

Data processing (Cost Explorer, last 30 days):
  - NAT Gateway data processing: 1,950 GB total ($87.75)
  - NAT Gateway base: 3 × $32.85 = $98.55
  - Total NAT cost: $186.30

Traffic breakdown (VPC Flow Logs, last 7 days, monthly projection):
  - S3: 0 GB (on Gateway endpoint)
  - DynamoDB: 0 GB (on Gateway endpoint)
  - ECR: 0 GB (on Interface endpoint)
  - Other AWS services: 150 GB/month
  - Internet: 1,800 GB/month

Workload context: production EKS cluster, high-throughput, requires multi-AZ
HA for outbound traffic.
