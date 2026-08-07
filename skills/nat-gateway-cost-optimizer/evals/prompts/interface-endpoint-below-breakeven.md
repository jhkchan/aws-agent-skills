# Eval prompt: interface-endpoint-below-breakeven

Optimise the NAT Gateway cost for the VPC below. The operator is considering
an ECR Interface endpoint. Walk the four-dimension analysis and emit the
standard optimisation block (VPC, VERDICT, REASON, RECOMMENDATION, SAVINGS,
IMPLEMENTATION). Pay close attention to the Interface endpoint break-even
maths before recommending.

VPC: vpc-interface-endpoint-below-breakeven
Region: us-east-1
Environment: production

NAT Gateways: 2 (us-east-1a, 1b), both available
Current VPC Endpoints:
  - S3 Gateway endpoint (com.amazonaws.us-east-1.s3), in route tables rtb-a, rtb-b

Data processing (Cost Explorer, last 30 days):
  - NAT Gateway data processing: 200 GB total ($9.00)
  - NAT Gateway base: 2 × $32.85 = $65.70

Traffic breakdown (VPC Flow Logs, last 7 days, monthly projection):
  - S3: 0 GB (already on Gateway endpoint)
  - ECR: 60 GB/month
  - Other AWS services: 40 GB/month
  - Internet: 100 GB/month

Operator question: "Should I add an ECR Interface endpoint to save on the
60 GB/month of ECR data-processing charges through NAT?"
