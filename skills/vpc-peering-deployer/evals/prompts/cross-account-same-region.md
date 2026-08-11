# Eval: cross-account-same-region

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — cross-account same-region peering, accepter account must accept, CIDR-based SG rules (SG cross-ref not supported cross-account)

## Prompt

Create a VPC peering connection between VPC vpc-prod111
(10.0.0.0/16) in account 123456789012 and VPC vpc-dev222
(10.2.0.0/16) in account 999999999999. Same region us-east-1.
Requester route table rtb-prod-rt. Accepter route table rtb-dev-rt.
No DNS resolution needed. Security group rules should use CIDR
(cross-account). Tags: Environment=prod-to-dev.
