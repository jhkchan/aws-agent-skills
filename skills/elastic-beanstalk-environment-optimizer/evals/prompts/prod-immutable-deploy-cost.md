# Eval: prod-immutable-deploy-cost

**Difficulty:** hard
**Branch:** FURTHER_OPTIMIZATION_AVAILABLE — prod keeps load-balanced + Immutable (correct for prod) but instances can be right-sized, managed updates enabled

## Prompt

Optimize a production Elastic Beanstalk environment my-prod-app
(e-xyz789abc). Load-balanced with 3x m5.xlarge across 2 AZs.
Average CPU is 28%. Deployment policy is Immutable (zero
downtime required for production). NAT Gateway present in
private subnets. Managed platform updates are disabled.
Termination protection is enabled.
