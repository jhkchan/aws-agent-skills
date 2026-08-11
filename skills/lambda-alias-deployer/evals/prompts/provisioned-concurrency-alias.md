# Eval: provisioned-concurrency-alias

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — provisioned concurrency on alias (not version), Auto Scaling at 70% target utilization

## Prompt

Set up provisioned concurrency on the prod alias for
my-function in us-east-1. 10 provisioned concurrent
executions. Configure Auto Scaling with 70% target
utilization, min 2, max 50. The alias points to version 5.
Account: 123456789012.
