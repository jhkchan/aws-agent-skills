# Eval: inter-region-peering

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — inter-region peering (us-east-1 to us-west-2), peer-region specified, cross-region data transfer cost noted, DNS resolution enabled

## Prompt

Create a VPC peering connection between VPC vpc-useast111
(172.16.0.0/16) in us-east-1 account 123456789012 and VPC
vpc-uswest222 (172.17.0.0/16) in us-west-2 account 123456789012.
This is for cross-region DR replication. Enable DNS resolution.
Requester route table rtb-useast-rt. Accepter route table
rtb-uswest-rt. Tags: Environment=dr, Topology=useast-to-uswest.
