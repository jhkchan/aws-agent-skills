# Baseline (no-skill) response: single-nat-cost-optimized

This file captures what a generic assistant produces WITHOUT the
vpc-network-deployer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, AZ-failure-risk FINDING, precise
route-table-per-AZ design, cost estimate).

---

Here's your staging VPC plan:

- VPC: 10.50.0.0/16 in us-west-2
- 2 AZs (us-west-2a, us-west-2b)
- Public and private subnets
- 1 NAT Gateway in AZ-a
- S3 and DynamoDB Gateway Endpoints

You can deploy this with the standard AWS CLI commands. The single NAT
Gateway will save you money in staging.

Monthly cost estimate: ~$32 for the NAT Gateway plus S3 storage for flow
logs.
