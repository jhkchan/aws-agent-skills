# Eval: authorized-accounts-cross-region

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — AccountAggregationSource, 3 accounts, us-east-1 + eu-west-1, per-account authorization, conformance pack on aggregator

## Prompt

Provision an AWS Config aggregator in us-east-1. Name:
authorized-accounts-aggregator. Type: authorized accounts.
Source accounts: 111111111111, 222222222222, 333333333333.
Regions: us-east-1, eu-west-1. Each source account will
call PutAggregationAuthorization for aggregator account
123456789012 in both regions. Conformance pack:
OperationalBestPractices-for-CloudWatch deployed on
aggregator account. Tags: Environment=production.
