# Eval: missing-cidr-overlap-check

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — both VPCs use 10.0.0.0/16; overlapping CIDRs break routing

## Prompt

Create a VPC peering connection between VPC vpc-alpha
(10.0.0.0/16) and VPC vpc-beta (10.0.0.0/16) in us-east-1. Both
in account 123456789012. The VPCs use the same CIDR block. Route
tables rtb-alpha and rtb-beta.
