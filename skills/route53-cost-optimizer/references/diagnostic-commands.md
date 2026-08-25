# Diagnostic Commands — Route 53 Cost Optimizer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight data-gate command listing

**Required data sources** (summarized — see reference for full CLI):
1. Hosted zone inventory: `aws route53 list-hosted-zones`
2. Per-zone record sets: `aws route53 list-resource-record-sets`
3. Health check inventory: `aws route53 list-health-checks`
4. Traffic policy inventory: `aws route53 list-traffic-policies`
5. Query logging configs: `aws route53 list-query-logging-configs`
6. DNS queries (14-30 day window): `aws cloudwatch get-metric-statistics --namespace AWS/Route53`
7. Cost Explorer breakdown: `aws ce get-cost-and-usage --filter "Service=Route53"`
