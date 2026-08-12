# End-to-end usage scenario: drift-detection-automator

A walkthrough showing the skill designing two drift detection workflows
for the same account: an AUTOMATION_DEPLOYED staging stack with daily
detection and auto-remediation, and a REVIEW_REQUIRED production stack
where auto-remediation is intentionally blocked. Demonstrates the
stack-class-based remediation gating and suppression rules.

## Input (user prompt)

> Design drift detection automation for our stacks. We have a staging
> web app (non-production, can auto-remediate) and a production payment
> service (critical, notify only). We want both monitored daily.

```
Design reference: prod-drift-rollout
Account: 111111111111
Region: us-east-1

Stack 1: staging-web-app
  Environment: staging (non-production)
  Resources: 15 (EC2, ALB, RDS, ASG, S3, IAM roles)
  Detection cadence: daily (02:00 UTC)
  SNS topic: arn:aws:sns:us-east-1:111111111111:drift-alerts
  SSM Automation: Custom-DriftRemediation (tested)
  Known-acceptable drift: ASG DesiredCapacity (scheduled scaling)
  Pre-prod validation: completed.

Stack 2: prod-payment-service
  Environment: production (critical)
  Resources: 42 (ECS, ALB, RDS Aurora, WAF, IAM, S3, SQS)
  Detection cadence: daily (02:00 UTC)
  SNS topic: arn:aws:sns:us-east-1:111111111111:drift-alerts-critical
  3 resources drifted: SecurityGroups (modified), IAM policy (changed),
    ALB listener rule (modified)
```

## Skill output

```text
DRIFT_AUTOMATION: prod-drift-rollout
STACK: staging-web-app
DETECTION:
  - Method: EventBridge scheduled (cron 0 2 * * ? *)
  - Cadence: daily at 02:00 UTC
  - Config rule: cloudformation-stack-drift-detection-check
COMPARISON:
  - Lambda: drift-detector
  - Severity classification: CRITICAL (SecurityGroups, IAM policies), MEDIUM (other)
  - Suppression rules: ASG DesiredCapacity, Lambda RoutingConfig
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:drift-alerts
  - Routing: CRITICAL -> page on-call | HIGH -> email | MEDIUM -> log
REMEDIATION:
  - Method: SSM Automation (CloudFormation change-set re-apply)
  - Auto-remediate: true (staging — non-production)
  - Approval gate: none (non-prod auto-remediation)
INTEGRATION:
  - Config Aggregator: enabled (cross-account visibility)
  - Drift report: s3://drift-reports/dt={date}/ + Athena table drift_reports
SAFETY:
  - Production protection: approval required (separate pipeline for prod)
  - Rollback: change-set rollback tested
  - Rate limiting: Lambda concurrency 5
AUDIT:
  - CloudTrail: cloudformation:DetectStackDrift, cloudformation:ExecuteChangeSet
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name drift-detection-daily --schedule-expression "cron(0 2 * * ? *)"

DRIFT_AUTOMATION: prod-drift-rollout
STACK: prod-payment-service
DETECTION:
  - Method: EventBridge scheduled (cron 0 2 * * ? *)
  - Cadence: daily at 02:00 UTC
COMPARISON:
  - Lambda: drift-detector
  - Severity: CRITICAL (3 resources: SG modified, IAM policy changed, ALB listener)
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:drift-alerts-critical
  - Routing: CRITICAL -> page on-call
REMEDIATION:
  - Method: MANUAL — SSM Change Manager approval required
  - Auto-remediate: BLOCKED (production stack)
SAFETY: production protection active, approval required
VERDICT: REVIEW_REQUIRED
GAP: Production drift detected but auto-remediation intentionally blocked. Operator must review 3 drifted resources. If intentional hotfixes from incident response, update the CFN template to match. If unintentional, create a change-set to revert. Do NOT auto-remediate without approval.
TEMPLATE: (SSM Automation with aws:approve gate — see Step 6)
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for staging +
REVIEW_REQUIRED for production.** Deploy the staging pipeline with auto-
remediation; the production pipeline requires human approval for any
remediation action.

## What the skill caught that a generic assistant misses

1. **The stack-class gate.** A generic assistant wires both stacks with
   auto-remediation. The skill refuses — production drift remediation
   requires human approval because re-applying the template may revert
   an intentional hotfix.

2. **The Config rule staleness gotcha.** A generic assistant deploys
   the Config rule and assumes it detects drift. The skill knows the
   rule reads the LAST drift result — it does NOT trigger new detection.
   The scheduled EventBridge trigger is what keeps the data current.

3. **The suppression rules.** A generic assistant ignores known-
   acceptable drift (ASG capacity changes from scheduled scaling). The
   skill configures suppression rules in SSM Parameter Store so
   ASG DesiredCapacity changes are classified as SUPPRESSED, not
   CRITICAL — eliminating false-positive noise.

4. **The change-set review gate.** A generic assistant uses `update-
   stack` directly. The skill always uses `create-change-set` first,
   reviews for resource replacements (downtime risk), and only then
   executes — with an `aws:approve` step for production.

5. **The drift report + Athena layer.** A generic assistant notifies
   on drift but provides no historical analysis. The skill exports
   drift reports to S3 with Athena tables for trend analysis: top
   drifted resource types, recurring drift patterns, cross-account
   summary.

6. **The API rate limit.** A generic assistant calls `detect-stack-
   drift` on all stacks simultaneously. The skill knows the API
   throttles at ~50 concurrent calls and uses SQS buffering for fleet-
   wide detection.

## Slash-command invocation

```
/aws:automate-drift-detection
```

Or via the orchestrator:

```
/aws:pipeline
You: "automate CloudFormation drift detection"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate drift detection"
# [Phase: Automate | Skills routed: drift-detection-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# List all stacks that support drift detection
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?EnableTerminationProtection!=null].StackName' \
  --region us-east-1 --profile default

# Check current drift status for a specific stack
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id <id> \
  --region us-east-1 --profile default

# Trigger drift detection manually
aws cloudformation detect-stack-drift \
  --stack-name staging-web-app \
  --region us-east-1 --profile default

# List existing Config rules for drift
aws configservice describe-config-rules \
  --query 'ConfigRules[?contains(ConfigRuleName, `drift`)]' \
  --region us-east-1 --profile default

# Check Config Aggregator status
aws configservice describe-configuration-aggregators \
  --region us-east-1 --profile default

# List StackSets
aws cloudformation list-stack-sets \
  --status ACTIVE \
  --region us-east-1 --profile default

# Check existing SSM Automation documents for drift remediation
aws ssm list-documents \
  --document-filter-list Key=DocumentType,Values=Automation \
  --filters Key=Name,Values=Drift \
  --region us-east-1 --profile default
```

Then paste the output into the skill for workflow design.
