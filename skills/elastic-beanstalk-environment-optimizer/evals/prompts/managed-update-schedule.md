# Eval: managed-update-schedule

**Difficulty:** medium
**Branch:** FURTHER_OPTIMIZATION_AVAILABLE — managed platform updates disabled, recommend enabling with off-peak schedule

## Prompt

Optimize a production Elastic Beanstalk environment
my-api-prod (e-api789jkl). Load-balanced with 2x c5.large.
Managed platform updates are currently disabled. The
environment runs a Node.js application with peak traffic
during business hours 09:00-18:00 UTC. Deployment policy is
Rolling. Termination protection enabled. Average CPU is 45%.
