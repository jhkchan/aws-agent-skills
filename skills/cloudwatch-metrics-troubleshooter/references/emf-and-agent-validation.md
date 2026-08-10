# CloudWatch EMF and agent validation reference

Canonical command snippets and validation patterns for the
`cloudwatch-metrics-troubleshooter` skill. Loaded when the skill needs
to inspect EMF blobs or CloudWatch agent config.

## 1. list-metrics — discover what exists

```bash
# All metrics under a namespace:
aws cloudwatch list-metrics --namespace <ns> --output table

# Specific metric across all namespaces:
aws cloudwatch list-metrics --metric-name CPUUtilization --output table

# Specific namespace + metric:
aws cloudwatch list-metrics --namespace AWS/ECS --metric-name CPUUtilization \
  --query 'Metrics[*].{ns:Namespace,name:MetricName,dimensions:Dimensions}' \
  --output json

# Paginate:
aws cloudwatch list-metrics --namespace <ns> --next-token <token>
```

## 2. get-metric-statistics — query what is retrievable

```bash
# Standard query:
aws cloudwatch get-metric-statistics \
  --namespace <ns> --metric-name <m> \
  --dimensions Name=ClusterName,Value=prod-app Name=ServiceName,Value=api \
  --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average Sum Maximum SampleCount \
  --query 'Datapoints[*].{ts:Timestamp,avg:Average,sum:Sum,max:Maximum,count:SampleCount}' \
  --output table

# Try every statistic to identify statistic mismatch:
for stat in Sum Average Maximum Minimum SampleCount; do
  echo "=== $stat ==="
  aws cloudwatch get-metric-statistics --namespace <ns> \
    --metric-name <m> --dimensions <dims> \
    --start-time <iso> --end-time <iso> --period <p> \
    --statistics $stat --query 'Datapoints[*].{ts:Timestamp,value:'$stat'}'
done
```

## 3. describe-alarms — read alarm config

```bash
aws cloudwatch describe-alarms --alarm-names <alarm> \
  --query 'MetricAlarms[0].{Namespace:Namespace,MetricName:MetricName,Dimensions:Dimensions,Period:Period,EvaluationPeriods:EvaluationPeriods,Statistic:Statistic,ComparisonOperator:ComparisonOperator,Threshold:Threshold,TreatMissingData:TreatMissingData,State:StateValue}'

# For metric math alarms, the Metrics array has the math:
aws cloudwatch describe-alarms --alarm-names <alarm> \
  --query 'MetricAlarms[0].Metrics'
```

## 4. CloudTrail LookupEvents — PutMetricData denials

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutMetricData \
  --start-time <iso> --end-time <iso> \
  --query 'Events[?errorCode!=`null`].{time:EventTime,user:Username,errorCode:errorCode,errorMessage:errorMessage}'
```

Look for `errorCode: AccessDenied`. The `errorMessage` names the
missing action.

## 5. IAM simulate-principal-policy — confirm PutMetricData permission

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <emitter-role-arn> \
  --action-names cloudwatch:PutMetricData \
  --resource-arns '*' \
  --query 'EvaluationResults[*].{action:EvalActionName,decision:EvalDecision}'
```

For namespace-scoped IAM, also include the namespace in the resource
ARN (e.g., `arn:aws:cloudwatch:*:<account>:metric-config/<namespace>`).

## 6. CloudWatch agent — config and log inspection

### Read the agent config

```bash
# On the host (EC2 / on-prem):
sudo cat /opt/aws/amazon-cloudwatch-agent/bin/config.json

# For SSM-managed agents, the config is in the Parameter Store:
aws ssm get-parameter --name AmazonCloudWatch-<config-name> --query 'Parameter.Value' --output text | jq .
```

A config with metrics enabled looks like:

```json
{
  "metrics": {
    "metrics_collected": {
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 60
      }
    },
    "namespace": "MyApp/Host"
  }
}
```

A missing `metrics` section is the most common cause of "agent is
running but no custom metrics appear."

### Read the agent log

```bash
sudo tail -100 /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log
```

Look for:
- `E! [outputs.cloudwatch] Failed to send metric data` — emission
  failure
- `AccessDeniedException` — IAM denial
- `InvalidParameterException` — config error

### Restart the agent after config edit

```bash
# EC2 / on-prem:
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/bin/config.json -s

# SSM-managed:
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -c ssm:AmazonCloudWatch-<config-name> -s
```

## 7. EMF — inspect the blob

### Locate the EMF log group

EMF blobs are written to a CloudWatch Logs group that the application
configures. Common patterns:
- `/aws/lambda/<function-name>` (Lambda with Powertools or EMF client)
- `/aws/ec2/<instance-id>/emf` (EC2 with EMF agent)
- `<app-defined>` (custom)

### Filter for recent EMF blobs

```bash
aws logs filter-log-events \
  --log-group-name <emf-log-group> \
  --filter-pattern '{ $._aws.CloudWatchMetrics = "*" }' \
  --start-time <epoch-ms> \
  --limit 5 \
  --query 'events[*].message'
```

If the filter returns nothing, the emitter is not writing EMF blobs
(or writing them malformed, which would not match the pattern).

### Validate the EMF structure

A valid EMF blob has:

```json
{
  "_aws": {
    "CloudWatchMetrics": [
      {
        "Namespace": "MyApp",
        "Dimensions": [["InstanceId"]],
        "Metrics": [
          { "Name": "Latency", "Unit": "Milliseconds" }
        ]
      }
    ],
    "Timestamp": 1691616000000
  },
  "InstanceId": "i-abc",
  "Latency": 42
}
```

Common malformations:

| Issue | Symptom |
|---|---|
| Missing `_aws` field | Blob ingested as log; no metric extracted |
| Missing `CloudWatchMetrics` array | Same |
| `Dimensions` not array of arrays | Silent drop |
| `Metrics` empty or missing `Name` | Silent drop |
| Metric value not at top level (nested under `_aws`) | Silent drop |
| `Timestamp` not epoch milliseconds | Rejected with error in some runtimes |
| Dimension value not at top level | Silent drop |

### EMF parsing tools

```bash
# Extract just the EMF directive for inspection:
aws logs filter-log-events \
  --log-group-name <emf-log-group> \
  --start-time <epoch-ms> --limit 5 \
  --query 'events[*].message' --output text \
  | jq '._aws'

# Count EMF blobs per hour (volume sanity check):
aws logs filter-log-events \
  --log-group-name <emf-log-group> \
  --filter-pattern '{ $._aws.CloudWatchMetrics = "*" }' \
  --start-time <epoch-ms> --end-time <epoch-ms> \
  --query 'searchedLogGroups[*].events | length(@)'
```

## 8. ECS Container Insights — verify enablement

```bash
aws ecs describe-cluster --cluster <name> \
  --query 'clusters[0].settings[?name==`containerInsights`].value'

# Enable if disabled:
aws ecs update-cluster-settings --cluster <name> \
  --settings name=containerInsights,value=enabled
```

New metrics take 3-5 minutes to appear.

## 9. EKS Container Insights — verify the agent

```bash
# Verify the CloudWatch agent DaemonSet:
kubectl get ds -n amazon-cloudwatch

# Verify pods are running:
kubectl get pods -n amazon-cloudwatch

# Read the agent config map:
kubectl get cm cloudwatch-agent-config -n amazon-cloudwatch -o yaml

# Read agent logs:
kubectl logs -n amazon-cloudwatch -l app=cloudwatch-agent --tail=100

# Verify the IRSA role annotation on the agent ServiceAccount:
kubectl get sa cloudwatch-agent -n amazon-cloudwatch -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'
```

For the newer CloudWatch Observability EKS add-on:

```bash
aws eks describe-addon --cluster-name <name> --addon-name amazon-cloudwatch-observability \
  --query 'addon.{status:status,health:healthIssues}'
```

## 10. RUM — verify the app monitor

```bash
aws rum list-app-monitors \
  --query 'AppMonitorSummaries[*].{name:Name,id:Id,state:State,region:Region}'

aws rum get-app-monitor --name <monitor-name> \
  --query 'AppMonitor.{name:Name,id:Id,state:State,appMonitorConfiguration:AppMonitorConfiguration}'

# CloudTrail for PutRumAppEvents denials:
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutRumAppEvents \
  --start-time <iso> --end-time <iso> \
  --query 'Events[?errorCode!=`null`]'
```

## 11. Cross-account observability — verify the link

```bash
# In the monitoring account:
aws cloudwatch list-included-accounts \
  --query 'AccountsWithLinkStatus'

# In the source account:
aws cloudwatch list-metric-streams
aws logs describe-account-policies --policy-type ACCOUNT_POLICY
```

Both sides must be configured. The monitoring account has a link; the
source account has a sharing policy.
