# Eval: gateway-endpoint-missing-route

**Difficulty:** hard
**Branch:** ROOT_CAUSE_IDENTIFIED — Gateway endpoint vpce-s3gw456 is in rtb-private-1 but NOT rtb-private-2; S3 traffic from subnet-private-2 goes via NAT Gateway

## Prompt

Diagnose a Gateway VPC endpoint vpce-s3gw456 for S3
(com.amazonaws.us-east-1.s3). The endpoint is available and in
route table rtb-private-1, but NOT in route table rtb-private-2.
Clients in subnet-private-2 report S3 traffic going through the
NAT Gateway instead of the endpoint. Endpoint policy is default.
