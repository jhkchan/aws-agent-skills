# End-to-end usage scenario: cost-anomaly-detection-automator

A walkthrough showing the skill designing two cost anomaly pipelines
for the same account: an AUTOMATION_DEPLOYED EC2 service-level monitor
with severity routing, and a REVIEW_REQUIRED auto-remediation pipeline
that targets production resources. Demonstrates the severity threshold
matrix and the production-impact safety gate.

## Input (user prompt)

> Set up cost anomaly detection for our account. We want EC2 spend
> anomalies routed by severity — Critical pages, High goes to Slack,
> Low gets logged. Also, we want a Lambda that auto-shuts-down ALL
> running instances when a Critical anomaly fires.

```
Design reference: prod-cost-anomaly-rollout
Account: 111111111111
Region: us-east-1

Requirement 1: EC2 service-level anomaly monitor with severity routing.
  - Critical (>=50%): page on-call via PagerDuty.
  - High (20-50%): notify Slack #finops-alerts.
  - Low (<20%): log to CloudWatch dashboard.
  - Lambda router: arn:aws:lambda:us-east-1:111111111111:function:cost-anomaly-router
  - Pre-prod validation: completed (synthetic spike confirmed in 18 hours).

Requirement 2: auto-remediation that stops ALL running EC2 instances
  (including production) on Critical anomaly.
  - Pre-prod validation: NOT completed.
  - Production-impact assessment: NOT done.
```

## Skill output

```text
ANOMALY: prod-cost-anomaly-rollout
MONITOR:
  - Name: ec2-spend-anomaly-monitor
  - Type: DIMENSION (SERVICE=Amazon Elastic Compute Cloud - Compute)
  - Status: ACTIVE
  - Scope: EC2 spend in account 111111111111
SUBSCRIPTION:
  - Severity routing: Critical (>=50%), High (20-50%), Low (<20%)
  - Endpoints: SNS arn:aws:sns:us-east-1:111111111111:critical-cost-alerts
  - Frequency: IMMEDIATE for Critical, DAILY for High, WEEKLY for Low
ROUTING:
  - Critical: SNS → Lambda cost-anomaly-router → PagerDuty + Slack #finops-critical
  - High: SNS → Lambda cost-anomaly-router → Slack #finops-alerts
  - Low: Lambda logs to CloudWatch dashboard
REMEDIATION:
  - Actions: tag untagged EC2 instances (notify-only for production)
  - Lambda: arn:aws:lambda:us-east-1:111111111111:function:cost-anomaly-router
  - Scope: non-production tagging; production = notify-only
  - Safety: dry-run tagging; production-impact assessment before any shutdown
AUDIT:
  - Budgets: monthly-cost-budget ($10K, 80% actual, 100% forecast)
  - Feedback: auto-true-positive for impact >= $200
  - Baseline: trailing 90-day EC2 average $2,340/day
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws ce create-anomaly-monitor --anomaly-monitor '{"MonitorName":"ec2-spend-anomaly-monitor","MonitorType":"DIMENSION","MonitorDimension":"SERVICE","MonitorSpecification":"{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Elastic Compute Cloud - Compute\"],\"MatchOptions\":[\"EQUALS\"]}}"}'
  aws ce create-anomaly-subscription --anomaly-subscription '{"SubscriptionName":"critical-cost-anomaly","Threshold":50.0,"Frequency":"IMMEDIATE","MonitorArn":"<monitor-arn>","Subscribers":[{"Address":"arn:aws:sns:us-east-1:111111111111:critical-cost-alerts","Type":"SNS"}]}'

ANOMALY: prod-cost-anomaly-rollout (auto-remediation)
MONITOR:
  - Name: ec2-spend-anomaly-monitor (existing)
  - Status: ACTIVE
SUBSCRIPTION:
  - Severity routing: wired (see above)
ROUTING:
  - Critical: SNS → Lambda (would trigger stop_instances)
REMEDIATION:
  - Actions: PROPOSED — stop ALL running EC2 instances (including production)
  - Lambda: NOT deployed (proposed logic is destructive)
  - Scope: ALL instances — NO production/non-prod filtering
  - Safety: NONE — no production-impact assessment
AUDIT:
  - Pre-prod validation: NOT completed
  - Production-impact assessment: NOT done
VERDICT: REVIEW_REQUIRED
GAP: Auto-remediation that stops ALL running instances (including production) is destructive without an impact assessment. Do NOT deploy this Lambda as described. Required before deployment: (1) scope auto-remediation to non-production instances only (filter by tag:Environment=non-prod); (2) complete pre-prod validation per the 3-cycle rule; (3) production-impact assessment for any prod-scoped action; (4) add a rollback/dry-run path. Until these gates are met, production auto-remediation is notify-only.
TEMPLATE: (see Step 5 for the safe Lambda pattern with non-prod filtering)
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for monitor +
severity routing + notify-only pipeline; REVIEW_REQUIRED for
production-instance auto-shutdown.**

## What the skill caught that a generic assistant misses

1. **The monitor-without-subscription trap.** A generic assistant
   creates the monitor and assumes alerts flow automatically. The skill
   explicitly wires subscriptions and verifies the SNS topic policy
   includes `events.costanomaly.amazonaws.com`.

2. **The severity routing design.** A generic assistant creates a single
   subscription with one threshold. The skill designs three tiers
   (Critical/High/Low) with different frequencies and endpoints.

3. **The Budgets-complementary insight.** A generic assistant treats
   Budgets and Anomaly Detection as interchangeable. The skill deploys
   both and explains that Budgets catch hard limits while Anomaly
   Detection catches pattern deviations.

4. **The production-impact gate.** A generic assistant writes the
   Lambda to stop all instances. The skill refuses — stopping production
   EC2 on a cost anomaly is destructive without an impact assessment.
   The skill scopes auto-remediation to non-prod and requires explicit
   gates for production.

5. **The feedback loop.** A generic assistant omits anomaly feedback.
   The skill includes auto-feedback submission to improve the ML model's
   false-positive rate over time.

## Slash-command invocation

```
/aws:automate-cost-anomaly-detection
```

Or via the orchestrator:

```
/aws:pipeline
You: "set up cost anomaly detection with severity routing"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate cost anomaly detection"
# [Phase: Automate | Skills routed: cost-anomaly-detection-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# List existing anomaly monitors
aws ce get-anomaly-monitors \
  --query 'AnomalyMonitors[].[MonitorName,MonitorType,MonitorStatus]' \
  --output table --region us-east-1 --profile default

# List existing anomaly subscriptions
aws ce get-anomaly-subscriptions \
  --query 'AnomalySubscriptions[].[SubscriptionName,Threshold,Frequency]' \
  --output table --region us-east-1 --profile default

# List existing budgets
aws budgets describe-budgets \
  --account-id 111111111111 \
  --query 'Budgets[].[BudgetName,BudgetLimit.Amount,TimeUnit]' \
  --output table --region us-east-1 --profile default

# Check top services by spend (for monitor targeting)
aws ce get-cost-and-usage \
  --time-period Start=2026-07-11,End=2026-08-11 \
  --granularity MONTHLY --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[0].Groups[].[Keys[0],Metrics.UnblendedCost.Amount]' \
  --output table --region us-east-1 --profile default

# Verify SNS topic policy includes Cost Anomaly Detection principal
aws sns get-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:critical-cost-alerts \
  --query 'Attributes.Policy' --region us-east-1 --profile default
```

Then paste the output into the skill for pipeline design.
