# Eval: same-account-same-region-dns

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — same-account same-region peering, DNS resolution both sides, SG cross-VPC reference (same acct+region), both-sides route tables

## Prompt

Create a VPC peering connection between VPC vpc-aaa11122
(10.0.0.0/16) and VPC vpc-bbb22233 (10.1.0.0/16) in us-east-1.
Same account 123456789012. Enable DNS resolution across the
peered VPCs. Requester route table rtb-app111. Accepter route
table rtb-data222. Security group sg-app should reference sg-data
from the accepter VPC for port 443. Tags: Environment=production,
Topology=app-to-data.
