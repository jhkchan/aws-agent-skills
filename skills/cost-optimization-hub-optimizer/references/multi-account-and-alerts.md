# Multi-Account and CloudWatch Alerts — Cost Optimization Hub

Deep reference on multi-account enrollment via the
Organizations Payer (the only anchor for org-wide visibility),
member-account opt-out and linkage verification, integration
with Compute Optimizer (the upstream source for right-size
recommendations), implementation-status tracking via
`update-recommendation-status`, and CloudWatch alerting on the
`CostOptimizationHub` namespace. Loaded on demand by the skill
— kept out of the main SKILL.md body so the optimization
procedure stays scannable.

## Multi-account enrollment via the Organizations Payer

### Why the payer is the only anchor

Cost Optimization Hub is a payer-side service. Multi-account
visibility requires enrollment FROM the Organizations Payer
(the management account) WITH `--include-member-accounts`.
Member-account-only enrollment sees only the member account,
not the org.

```bash
# From the Payer (management) account
aws cost-optimization-hub update-enrollment-status \
  --status ACTIVE \
  --include-member-accounts

# Verify linkage across member accounts
aws cost-optimization-hub get-enrollment-statuses \
  --query 'items[*].{Account:accountId,Status:status,Included:includeMemberAccounts}' \
  --output table
```

### Member-account opt-out

A member account can opt OUT of Hub visibility by re-issuing
`update-enrollment-status` from the member account with
`--status INACTIVE` and `--no-include-member-accounts`. The
payer loses visibility into that account's resources. Common
use case: regulated environments where the payer should not
see resource-level detail.

### Verification commands

```bash
# Payer-side: list member accounts the Hub can see
aws cost-optimization-hub get-enrollment-statuses \
  --query 'items[?status==`ACTIVE`].accountId' --output text

# Compare against Organizations list
aws organizations list-accounts \
  --query 'Accounts[*].Id' --output text

# The two lists should match unless a member has opted out
```

### Common multi-account pitfalls

1. **Enabling the Hub from a member account and expecting
   org-wide visibility.** Member-account enrollment sees only
   the member. Multi-account visibility is payer-anchored.

2. **Forgetting `--include-member-accounts`.** Without the
   flag, the Hub enrolls the payer only. Member accounts are
   invisible until you re-issue with the flag.

3. **Member that joined the org after enablement is invisible
   for up to 24h.** Hub linkage refreshes on its daily cycle.
   New member accounts appear in the next refresh.

4. **Cross-Region aggregation.** The Hub aggregates across
   Regions automatically — no per-region enablement needed.
   But Compute Optimizer must be enrolled in EACH Region
   where compute runs.

## Integration with Compute Optimizer

### Why CO gates the Hub's right-size recommendations

Compute Optimizer (CO) is the upstream source for right-size
recommendations on EC2, EC2 Auto Scaling groups, and Lambda.
Without CO enrolled, the Hub returns ZERO right-size
recommendations for those resource types.

```bash
# Check CO enrollment
aws compute-optimizer get-enrollment-status

# Enable CO (if not already)
aws compute-optimizer update-enrollment-status \
  --status Active \
  --include-member-accounts
```

### CO enrollment scope

CO enrollment takes up to 12 hours to surface its first
findings. The Hub refreshes daily. Plan for a 24-36h lag
between enabling CO and seeing right-size recommendations in
the Hub.

| CO resource type | Hub recommendation | Notes |
|---|---|---|
| EC2 instance | EC2 right-size | Requires CloudWatch agent for memory metrics |
| EC2 Auto Scaling group | ASG right-size | Group-level recommendation |
| Lambda function | Lambda right-size | CPU + memory tuning |
| EBS volume | EBS right-size | Native to Hub, NOT from CO |
| ECS service / Fargate | ECS right-size | Native to Hub, NOT from CO |

### CloudWatch agent prerequisite for memory metrics

CO uses CPU metrics natively but requires the CloudWatch agent
for memory utilization. Without memory metrics, CO returns
CPU-only recommendations, which can under-recommend. Install
the CloudWatch agent on EC2 instances for full fidelity.

```bash
# Verify CloudWatch agent is reporting memory
aws cloudwatch get-metric-statistics \
  --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Values=i-xxx \
  --start-time $(($(date +%s) - 3600)) \
  --end-time $(date +%s) --period 300 \
  --statistics Average --output table
```

## Implementation-status tracking

### Status semantics

| Status | Meaning | Effect on verdict |
|---|---|---|
| PENDING | Default; not yet acted on | Blocks OPTIMIZED |
| APPLIED | Optimization applied | OK if savings verified |
| IGNORED | Deliberately not applying | OK if rationale documented |

The Hub does NOT verify whether the optimization actually
shipped. APPLIED is an operator assertion. Verify savings
realization via Cost Explorer after the next billing cycle.

### Update API

```bash
# Single
aws cost-optimization-hub update-recommendation-status \
  --recommendation-id <id> \
  --status APPLIED

# Batch
aws cost-optimization-hub batch-update-recommendation-status \
  --request '{"recommendationIds":["id1","id2","id3"],"status":"IGNORED"}'

# Filter by status
aws cost-optimization-hub get-recommendations \
  --filter '{"implementationStatus":"PENDING"}'
```

### The OPTIMIZED verdict rule

OPTIMIZED requires:

1. Hub enrollment ACTIVE.
2. Compute Optimizer ACTIVE (so right-size coverage is
   meaningful).
3. Zero PENDING recommendations with positive
   `estimatedMonthlySavings`.

The third rule is the load-bearing one. APPLIED with no
savings realization is still APPLIED. IGNORED with documented
rationale is OK. PENDING is the blocker.

### Documenting IGNORED rationale

The Hub does not have a free-text rationale field for IGNORED.
Use the resource tag or an external tracker (Jira, Notion) and
reference the tag in the IGNORED batch.

```bash
# Tag the resource with the rationale
aws ec2 create-tags --resources i-xxx \
  --tags Key=COHIgnoreReason,Value="legacy-app-cannot-resize"

# Then mark IGNORED in the Hub
aws cost-optimization-hub update-recommendation-status \
  --recommendation-id <id-for-i-xxx> \
  --status IGNORED
```

## CloudWatch alerting on the CostOptimizationHub namespace

### Available metrics

The Hub publishes the following metrics to the
`CostOptimizationHub` namespace once enrollment is ACTIVE.
Metric publish happens on the daily refresh cycle.

| Metric | Meaning |
|---|---|
| `ResourceCount` | Number of resources analyzed |
| `RecommendationCount` | Number of recommendations produced |
| `EstimatedMonthlySavings` | Aggregate estimated monthly savings (USD) |

### Common alarm shapes

```bash
# Alarm 1: new recommendations appeared (triage queue grew)
aws cloudwatch put-metric-alarm \
  --alarm-name "CostOptHub-New-Recommendations" \
  --namespace CostOptimizationHub \
  --metric-name RecommendationCount \
  --statistic Maximum \
  --period 86400 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:111122223311:finops-alerts"

# Alarm 2: estimated savings jumped (new waste appeared)
aws cloudwatch put-metric-alarm \
  --alarm-name "CostOptHub-Savings-Increase-25pct" \
  --namespace CostOptimizationHub \
  --metric-name EstimatedMonthlySavings \
  --statistic Maximum \
  --period 86400 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --treat-missing-data notBreaching \
  --alarm-actions "arn:aws:sns:us-east-1:111122223311:finops-alerts"

# Alarm 3: estimated savings dropped (progress or regression)
# Use anomaly detection on EstimatedMonthlySavings for
# smooth detection rather than a static threshold.
```

### Daily digest via EventBridge + Lambda

```python
import boto3, json

hub = boto3.client('cost-optimization-hub')
sns = boto3.client('sns')

def lambda_handler(event, context):
    summary = hub.get_recommendation_summary()
    msg = (
        f"Cost Optimization Hub Daily Digest\n"
        f"  Total recommendations: {summary.get('recommendationCount', 0)}\n"
        f"  Estimated monthly savings: ${summary.get('estimatedMonthlySavings', 0):,.2f}\n"
        f"  Last refresh: {summary.get('lastRefresh', 'unknown')}\n"
    )
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:111122223311:finops-daily-digest',
        Subject='CostOptHub Daily Digest',
        Message=msg,
    )
    return {'statusCode': 200}
```

Trigger the function daily via an EventBridge rule:

```bash
aws events put-rule \
  --name "costopthub-daily-digest" \
  --schedule-expression "cron(0 13 ? * MON-FRI *)"

aws events put-targets \
  --rule costopthub-daily-digest \
  --targets '{"Id":"1","Arn":"arn:aws:lambda:us-east-1:111122223311:function:costopthub-digest"}'
```

### Common alerting pitfalls

1. **Namespace publishes only when enrollment is ACTIVE.**
   Creating alarms before enrollment produces no data; the
   alarm stays INSUFFICIENT_DATA.

2. **Metrics publish on the daily refresh cycle.** Alarms with
   sub-day periods are noisy. Use 86400-second (1-day) periods
   for stable alerts.

3. **`EstimatedMonthlySavings` drops when you apply
   recommendations.** A drop is expected progress, not a
   regression. Use a separate "applied savings" tracker (via
   Cost Explorer) to celebrate wins.

4. **Member-account opt-out breaks org-wide alarms.** If a
   member opts out, the payer's `ResourceCount` drops.
   Distinguish "applied recommendations" from "lost
   visibility."

## Terraform example: multi-account + CloudWatch alarms

```hcl
resource "aws_costoptimizationhub_enrollment_status" "this" {
  include_member_accounts = true
}

resource "aws_costoptimizationhub_preferences" "this" {
  savings_estimation_mode  = "AFTER_DISCOUNT"
  look_back_period_in_days = 14

  depends_on = [aws_costoptimizationhub_enrollment_status.this]
}

# CloudWatch alarm for new recommendations
resource "aws_cloudwatch_metric_alarm" "new_recommendations" {
  alarm_name          = "CostOptHub-New-Recommendations"
  namespace           = "CostOptimizationHub"
  metric_name         = "RecommendationCount"
  statistic           = "Maximum"
  period              = 86400
  threshold           = 1
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  alarm_actions       = [aws_sns_topic.finops_alerts.arn]

  depends_on = [aws_costoptimizationhub_enrollment_status.this]
}

# Compute Optimizer enrollment (gates right-size recommendations)
resource "aws_compute_optimizer_enrollment_status" "this" {
  status                  = "Active"
  include_member_accounts = true
}
```
