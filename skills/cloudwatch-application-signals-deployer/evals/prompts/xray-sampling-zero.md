# Eval: xray-sampling-zero

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — X-Ray sampling disabled

## Prompt

Enable CloudWatch Application Signals on the notifications-api
service running on ECS Fargate in us-east-1. Runtime: Java 17.
The task role has both required managed policies. The X-Ray
Default sampling rule is currently set to FixedRate=0 (was
disabled during a cost-reduction sweep). Create a 99.9%
availability SLO. Account: 123456789012.
