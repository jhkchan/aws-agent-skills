# Diagnostic Commands — DevOps Guru Troubleshooter

Full copy-pasteable CLI command sequence for the 9-step diagnostic
walk. Variables to substitute: `<insight-id>`, `<region>`,
`<account-id>`, `<time-range>`.

## Step 0: Capture the insight

```bash
# List OPEN insights (sorted by severity, most recent first)
aws devops-guru list-insights --region <region> \
  --status-filter AnyOpenInsights \
  --query 'ProactiveInsights[*].{id:Id,severity:Severity,name:Name,resourcetype:ResourceCollection}' \
  --output table

aws devops-guru list-insights --region <region> \
  --status-filter AnyOpenInsights \
  --query 'ReactiveInsights[*].{id:Id,severity:Severity,name:Name,resourcetype:ResourceCollection}' \
  --output table
```

## Step 1: describe-insight (full detail)

```bash
aws devops-guru describe-insight --region <region> \
  --insight-id <insight-id> \
  --query 'ProactiveInsight.{name:Name,description:Description,severity:Severity,status:Status,start:InsightTimeRange.StartTime,end:InsightTimeRange.EndTime}' \
  --output table

# For Reactive insights, query .ReactiveInsight instead
aws devops-guru describe-insight --region <region> \
  --insight-id <insight-id> \
  --query 'ReactiveInsight.{name:Name,description:Description,severity:Severity,status:Status,start:InsightTimeRange.StartTime,end:InsightTimeRange.EndTime}'
```

## Step 2: list-anomalies-for-insight

```bash
aws devops-guru list-anomalies-for-insight --region <region> \
  --insight-id <insight-id> \
  --start-time-range '{From=2026-08-09T00:00:00Z,To=2026-08-10T23:59:59Z}' \
  --query 'ProactiveAnomalies[*].{name:Name,source:Source,severity:Severity,description:Description}' \
  --output table

# For Reactive insights, query .ReactiveAnomalies instead
```

## Step 3: list-recommendations

```bash
aws devops-guru list-recommendations --region <region> \
  --insight-id <insight-id> \
  --query 'Recommendations[*].{name:Name,description:Description,category:Category,link:Link}' \
  --output table
```

Recommendation categories:
- `AGGREGATE_OF_EVENT_LOGS` — CloudWatch Logs patterns
- `AGGREGATE_OF_METRICS` — CloudWatch metric patterns
- `DEPLOYMENT_FAILURE` — deployment event correlation
- `LOG_PATTERN` — specific log patterns

## Step 4: list-events (2024-2025 feature)

```bash
aws devops-guru list-events --region <region> \
  --insight-id <insight-id> \
  --query 'Events[*].{time:Time,source:DataSource,name:Name,type:Type,resource:ResourceCollection}' \
  --output table
```

Surfaces correlated CloudTrail, CloudWatch, and deployment events
without manual cross-referencing.

## Step 5: CloudWatch metric correlation

```bash
# Get the actual metric values for the anomaly time range
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/my-alb/1234567890 \
  --start-time 2026-08-09T14:00:00Z \
  --end-time 2026-08-09T15:00:00Z \
  --period 300 --statistics Average,Maximum \
  --query 'Datapoints[*].[Timestamp,Average,Maximum]' --output table

# RDS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=prod-db \
  --start-time 2026-08-09T14:00:00Z \
  --end-time 2026-08-09T15:00:00Z \
  --period 300 --statistics Average,Maximum \
  --query 'Datapoints[*].[Timestamp,Average,Maximum]' --output table

# Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=checkout-handler \
  --start-time 2026-08-10T09:30:00Z \
  --end-time 2026-08-10T10:30:00Z \
  --period 300 --statistics Average,p99 \
  --query 'Datapoints[*].[Timestamp,Average]' --output table
```

## Step 6: CloudTrail change-correlation

```bash
# Look for infrastructure changes in the 2 hours before the insight
aws cloudtrail lookup-events \
  --start-time 2026-08-09T12:35:00Z \
  --end-time 2026-08-09T14:35:00Z \
  --query 'Events[*].[EventTime,Username,EventName,ResourceName]' \
  --output table

# Filter for specific high-impact events
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=UpdateStack \
  --start-time 2026-08-09T12:35:00Z \
  --end-time 2026-08-09T14:35:00Z

aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=FailoverDBCluster \
  --start-time 2026-08-10T03:00:00Z \
  --end-time 2026-08-10T03:30:00Z
```

## Step 7: Deployment history

```bash
# CodeDeploy deployments in the time window
aws deploy list-deployments \
  --application-name <app-name> \
  --create-time-range start=2026-08-09T12:00:00Z,end=2026-08-09T14:35:00Z

# CodePipeline executions
aws codepipeline list-pipeline-executions \
  --pipeline-name <pipeline-name> \
  --query 'pipelineExecutionSummaries[*].[startTime,status,lastUpdateTime]' \
  --output table

# CloudFormation stack changes
aws cloudformation describe-stack-events --stack-name <stack-name> \
  --query 'StackEvents[?Timestamp>`"2026-08-09T12:00:00Z"`].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId,ResourceStatusReason]' \
  --output table
```

## Step 8: Resource health (DevOps Guru)

```bash
# Check resource health for a specific resource
aws devops-guru describe-resource-health --region <region> \
  --resource-arn <resource-arn>

# Get the full resource collection under DevOps Guru coverage
aws devops-guru get-resource-collection --region <region> \
  --resource-collection-type AWS::CloudFormation::Stack
```

## Step 9: AWS Health Dashboard correlation

```bash
# For AWS-side events (AZ outages, service degradations)
aws health describe-events \
  --region us-east-1 \
  --query 'events[?startTime>=`"2026-08-10T03:00:00Z"`].[eventArn,service,statusCode,startTime,endTime]' \
  --output table
```

Note: `aws health` requires Business, Enterprise On-Ramp, or Enterprise
Support. For lower-tier support, check the AWS Health Dashboard in the
console.

## Verification after remediation

```bash
# Re-check the insight status (expect RESOLVED after fix)
aws devops-guru describe-insight --region <region> \
  --insight-id <insight-id> \
  --query 'ProactiveInsight.Status'

# CloudWatch metric back to baseline
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/my-alb/1234567890 \
  --start-time 2026-08-09T15:00:00Z \
  --end-time 2026-08-09T16:00:00Z \
  --period 300 --statistics Average \
  --query 'Datapoints[*].[Timestamp,Average]' --output table
```
