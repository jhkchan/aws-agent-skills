# Eval: blue-green-cname-swap

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — green environment deployed, CNAME swap procedure, rollback path

## Prompt

Set up a blue-green deployment for Elastic Beanstalk application myapp
in us-east-1. Blue environment myapp-blue is currently serving traffic
(environment-id e-blue123). Deploy green environment myapp-green with
version v2 using the same configuration template myapp-prod-template.
Platform: 64bit Amazon Linux 2023 v6.0.4 running Node.js 20. ALB,
immutable deployment policy, enhanced health enabled. Once green is
Ready and Green health, swap CNAMEs.
