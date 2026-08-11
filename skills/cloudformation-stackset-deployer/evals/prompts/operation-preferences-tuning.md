# Eval: operation-preferences-tuning

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — FailureTolerancePercentage=5, MaxConcurrentPercentage=20, RegionOrder, CAPABILITY_AUTO_EXPAND

## Prompt

Create a SERVICE_MANAGED StackSet named ssm-patch-baseline
targeting ou-def-11223344 across us-east-1, us-east-2,
us-west-2, and eu-west-1. Template at
s3://templates/patch-baseline.yaml (24,000 bytes).
Trusted access enabled. Set operation preferences:
FailureTolerancePercentage=5, MaxConcurrentPercentage=20,
RegionConcurrencyType=SEQUENTIAL, RegionOrder starting with
us-east-1. Capabilities: CAPABILITY_AUTO_EXPAND.
Account ID: 111111111111.
