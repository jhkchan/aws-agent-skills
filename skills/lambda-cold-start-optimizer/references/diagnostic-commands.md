# Diagnostic and pre-flight commands — lambda-cold-start-optimizer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Pre-flight data gate — required data sources

Cold-start optimization decisions require init-duration telemetry. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/cold-start-metrics-and-power-tuning.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Function configuration: `aws lambda get-function-configuration`
2. Duration + InitDuration (14-30 day window): `aws cloudwatch get-metric-statistics` with Lambda Insights
3. Cold-start count: Lambda Insights `coldStarts` metric or `Invocations` vs unique container IDs
4. SnapStart config: `aws lambda get-function-configuration --query 'SnapStart'`
5. Provisioned concurrency configs: `aws lambda list-provisioned-concurrency-configs`
6. VPC config: `aws lambda get-function-configuration --query 'VpcConfig'`
7. Tracing config: `aws lambda get-function-configuration --query 'TracingConfig'`
8. Package size: `aws lambda get-function-configuration --query 'CodeSize'`

## VPC cold-start diagnostic CLI (moved from SKILL.md Step 5)

**VPC cold-start diagnostic CLI:**
```bash
aws ec2 describe-network-interfaces \
  --filters Name=description,Values="AWS Lambda VPC ENI*" \
  --query 'NetworkInterfaces[*].{Id:NetworkInterfaceId,Subnet:SubnetId,Status:Status}' \
  --output table

aws ec2 describe-subnets --subnet-ids <subnet-ids-from-VpcConfig> \
  --query 'Subnets[*].{SubnetId:SubnetId,AvailableIPs:AvailableIpAddressCount,CIDR:CidrBlock}' \
  --output table
```

