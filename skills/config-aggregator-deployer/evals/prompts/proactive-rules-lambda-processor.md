# Eval: proactive-rules-lambda-processor

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — proactive Config rules (StartResourceEvaluation), Lambda processor org config rule for custom compliance

## Prompt

Provision an AWS Config aggregator in us-east-1. Name:
org-compliance-aggregator. Organization ID: o-abc123def.
Delegated admin: 123456789012. Deploy a proactive Config
rule s3-bucket-versioning-proactive (Proactive mode enabled)
for pre-deployment resource evaluation. Deploy an
organization config rule custom-encryption-check with
Lambda processor function config-encryption-evaluator
(runtime python3.12, role ConfigLambdaRole). Source: all
accounts, all regions. Tags: Environment=production.
