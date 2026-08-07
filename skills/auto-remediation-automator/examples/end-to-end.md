# End-to-end usage scenario: auto-remediation-automator

A walkthrough showing the skill designing two remediation workflows
for the same account: an AUTOMATED S3 public-access workflow and a
MANUAL_STEP_REQUIRED IAM-policy-detach workflow that must route
through SSM Change Manager. Demonstrates the trigger matrix and the
destructive-remediation safety gate.

## Input (user prompt)

> Design auto-remediation for our Config findings. We have S3 public
> buckets (managed rule, reversible) and IAM users with PowerUserAccess
> we want to strip (custom Lambda rule). We want both fully automated.

```
Design reference: prod-remediation-rollout
Account: 111111111111
Region: us-east-1

Rule 1: s3-bucket-public-read-prohibited (AWS-managed)
  Scope: AWS::S3::Bucket
  Sample NON_COMPLIANT: app-uploads-bucket-prod
  Pre-prod validation: completed (5 buckets tested, all flipped COMPLIANT).
  SSM service role ARN:
    arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole

Rule 2: custom-iam-no-power-user (custom Lambda)
  Scope: AWS::IAM::User
  Sample NON_COMPLIANT: prod-app-svc-user (attached PowerUserAccess)
  The user is the production app service account.
  Pre-prod validation: not started.
```

## Skill output

```text
REMEDIATION: prod-remediation-rollout
RULE: s3-bucket-public-read-prohibited
RESOURCE_TYPE: AWS::S3::Bucket
WORKFLOW:
  - Detection: AWS-managed Config rule s3-bucket-public-read-prohibited, scoped to AWS::S3::Bucket.
  - Runbook: AWS-DisableS3BucketPublicAccess (AWS-managed, floating version).
  - Trigger: AUTOMATIC (reversible fix; pre-prod validated; CloudTrail alarm configured).
  - Safety gates: MaximumAutomaticAttempts=3, RetryAttemptSeconds=600, CloudTrail alarm, Config timeline verification.
  - Audit: describe-remediation-execution-status + get-resource-config-history.
TRIGGER: AUTOMATIC
SAFETY: retry-limit, cloudtrail-alarm, config-verification
AUDIT:
  - aws configservice describe-remediation-execution-status --config-rule-name s3-bucket-public-read-prohibited
  - aws configservice get-resource-config-history --resource-type AWS::S3::Bucket --resource-id <bucket>
VERDICT: AUTOMATED
GAP: None
TEMPLATE:
  aws configservice put-remediation-configurations --remediation-configurations '[{"ConfigRuleName":"s3-bucket-public-read-prohibited","TargetType":"SSM_DOCUMENT","TargetId":"AWS-DisableS3BucketPublicAccess","Automatic":true,"MaximumAutomaticAttempts":3,"RetryAttemptSeconds":600,"Parameters":{"S3BucketName":{"ResourceValue":{"Value":"RESOURCE_ID"}},"AutomationAssumeRole":{"StaticValue":{"Values":["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}}}]'

REMEDIATION: prod-remediation-rollout
RULE: custom-iam-no-power-user
RESOURCE_TYPE: AWS::IAM::User
WORKFLOW:
  - Detection: Custom Lambda Config rule on AWS::IAM::User.
  - Runbook: NONE — detaching PowerUserAccess from the production service account
    is a destructive change that will break the application.
  - Trigger: MANUAL via SSM Change Manager (per Step 9 safety gate).
  - Safety gates: Change Template + approval workflow required before execution.
  - Audit: CloudTrail on ssm:StartAutomationExecution + Config timeline.
TRIGGER: MANUAL
SAFETY: NONE for automation — change-manager-required
AUDIT: NOT WIRED until Change Template is approved
VERDICT: MANUAL_STEP_REQUIRED
GAP: Destructive remediation on a production application identity. Do NOT configure Automatic: true. Route through SSM Change Manager: (1) build a Change Template referencing the detachment runbook; (2) require approval from the application owner; (3) schedule a maintenance window; (4) verify application health after the change. Switching to automatic without these gates will cause an immediate production outage.
TEMPLATE: (SSM Change Manager Change Template — see Step 9)
```

**Account-level aggregate verdict: AUTOMATED for S3 + MANUAL_STEP_REQUIRED
for IAM.** Roll out the S3 workflow immediately; the IAM workflow
requires the Change Manager pipeline before any production wiring.

## What the skill caught that a generic assistant misses

1. **The destructive-change gate.** A generic assistant wires both
   rules with `Automatic: true`. The skill refuses — detaching
   `PowerUserAccess` from a production service account is destructive,
   so the workflow must route through SSM Change Manager with an
   approval gate.

2. **The pre-prod validation gate.** A generic assistant skips
   validation. The skill requires pre-prod testing on at least 3
   sample NON_COMPLIANT resources before flipping from MANUAL to
   AUTOMATIC trigger.

3. **The backlog gotcha.** A generic assistant omits
   `start-remediation-execution`. The skill flags that
   `Automatic: true` does NOT remediate the existing 5 buckets
   already NON_COMPLIANT — only future evaluations. The operator must
   run `start-remediation-execution` per existing resource.

4. **The conformance-pack remediation distinction.** A generic
   assistant ships a conformance pack and assumes remediation is
   wired. The skill notes the pack must include explicit
   `RemediationConfiguration` resources and verifies with
   `describe-remediation-configurations` after deployment.

## Slash-command invocation

```
/aws:automate-remediation-workflow
```

Or via the orchestrator:

```
/aws:pipeline
You: "design auto-remediation for Config findings"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate Config remediation"
# [Phase: Automate | Skills routed: auto-remediation-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Discover Config rules with NON_COMPLIANT resources
aws configservice describe-compliance-by-config-rule \
  --compliance-types NON_COMPLIANT --region us-east-1 --profile default

# Check whether remediation is already wired
aws configservice describe-remediation-configurations \
  --config-rule-names <rule-name> --region us-east-1 --profile default

# Check existing remediation executions
aws configservice describe-remediation-execution-status \
  --config-rule-name <rule-name> \
  --resource-type AWS::S3::Bucket --resource-id <bucket> \
  --region us-east-1 --profile default

# Verify the SSM service role exists
aws iam get-role --role-name AWS-SSM-AutomationExecutionRole \
  --query 'Role.Arn' --output text

# Check SSM managed runbook availability in region
aws ssm list-documents \
  --document-filter-list Key=DocumentType,Values=Automation \
  --filters Key=Owner,Values=Amazon \
  --query 'DocumentIdentifiers[?starts_with(Name,`AWS-`)].Name' \
  --region us-east-1 --profile default --output text
```

Then paste the output into the skill for workflow design.
