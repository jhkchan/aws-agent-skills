# Eval: nat-gateway-elimination

**Difficulty:** medium
**Branch:** OPTIMIZED — staging single-instance with public IP, NAT Gateway eliminated (~$32/mo savings), uses IGW

## Prompt

Optimize a staging Elastic Beanstalk environment my-staging-app
(e-stg456ghi). Single-instance with 1x t3.medium. The instance
has a public IP (54.210.x.x). A NAT Gateway is present in the
VPC costing about $32/mo. Average CPU is 18%. The instance is
in a public subnet with IGW access.
