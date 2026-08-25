# Diagnostic and pre-flight commands — lambda-cost-optimizer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Pre-flight data gate — required data sources

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/lambda-pricing-and-power-tuning.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Function configuration: `aws lambda get-function-configuration`
2. Duration + Invocations (14-30 day window): `aws cloudwatch get-metric-statistics`
3. Memory utilization (Lambda Insights): `aws cloudwatch get-metric-statistics --namespace LambdaInsights`
4. Compute Optimizer findings: `aws compute-optimizer get-lambda-function-recommendations`
5. Event source mappings: `aws lambda list-event-source-mappings`
6. Provisioned concurrency configs: `aws lambda list-provisioned-concurrency-configs`

