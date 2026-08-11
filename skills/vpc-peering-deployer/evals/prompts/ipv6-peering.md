# Eval: ipv6-peering

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — dual-stack peering with IPv4 and IPv6 routes on both sides, IPv6 CIDRs cited

## Prompt

Create a VPC peering connection between VPC vpc-app-v6
(10.10.0.0/16, IPv6 2600:1f18:4113:a100::/56) and VPC vpc-data-v6
(10.11.0.0/16, IPv6 2600:1f18:4113:b200::/56) in us-east-1, account
123456789012. Both IPv4 and IPv6 traffic needed. Requester route
table rtb-app-v6. Accepter route table rtb-data-v6. Tags:
Environment=production, Protocol=dualstack.
