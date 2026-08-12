# Eval: dev-single-instance-migration

**Difficulty:** hard
**Branch:** OPTIMIZED — dev environment migrated from load-balanced (2x t3.medium + ELB + NAT) to single-instance (1x t3.small), Immutable changed to All at Once

## Prompt

Optimize a dev Elastic Beanstalk environment my-dev-app
(e-abc123def). Currently load-balanced with 2x t3.medium
instances, an Application Load Balancer, and a NAT Gateway in
us-east-1. Average CPU utilization is 12% over the past 14 days.
Deployment policy is Immutable. The environment is for
development only, brief downtime is acceptable.
