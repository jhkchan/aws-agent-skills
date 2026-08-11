# Eval: arc-routing-control-with-safety-rule

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ARC with safety rule + readiness check cited

## Prompt

Set up Route 53 ARC for an active-passive DR topology. Cluster
"api-dr-cluster", control panel "api-dr-panel", routing controls
"us-east-1-routing" and "us-west-2-routing". Mandatory safety
rule that blocks both-off. Readiness check on the us-west-2 API
Gateway stage ARN
"arn:aws:apigateway:us-west-2::/apis/abc123/stages/prod".
