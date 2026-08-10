# End-to-end usage scenario: config-rule-deployer

A walkthrough showing the skill creating a managed S3 security Config
rule with auto-remediation, a custom Lambda tag-enforcement rule, and
an organization config rule that is blocked by a member-account
deployment attempt. Each path includes pre-checks, CONFIRM gate, and
post-verification — and is contrasted with the PREREQUISITES_MISSING
case where pre-checks catch a problem.

## Input (user prompt)

> Create a managed Config rule s3-bucket-public-read-prohibited with
> auto-remediation via AWS-DisableS3BucketPublicReadWrite. Then deploy
> a custom Lambda rule for EC2 required tags. Then try to deploy an
> org rule from a member account (should fail).

```json
{
  "Operation": "create",
  "Rule name": "s3-bucket-public-read-prohibited",
  "Type": "managed",
  "ManagedRuleIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
  "Scope": "AWS::S3::Bucket",
  "Remediation": {
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "AWS-DisableS3BucketPublicReadWrite",
    "Automatic": true
  },
  "Region": "us-east-1",
  "Account": "111111111111",
  "PreChecks": {
    "describe-configuration-recorders": {"recording": true, "allSupported": true},
    "describe-delivery-channels": {"s3BucketName": "config-bucket-111111111111", "bucketExists": true},
    "describe-config-rules.count": 12,
    "ssm.describe-document.AWS-DisableS3BucketPublicReadWrite": {"exists": true}
  }
}
```

## Skill output — managed rule with remediation

```text
RULE: s3-bucket-public-read-prohibited
VERDICT: READY_TO_DEPLOY
TARGET: s3-bucket-public-read-prohibited
PRE_CHECKS:
  - [PASS] Configuration recorder active (recording = true, allSupported = true)
  - [PASS] Delivery channel configured (S3 bucket: config-bucket-111111111111 exists)
  - [PASS] ManagedRuleIdentifier S3_BUCKET_PUBLIC_READ_PROHIBITED valid
  - [PASS] Scope AWS::S3::Bucket is a supported resource type
  - [PASS] IAM principal holds config:PutConfigRule
  - [PASS] SSM document AWS-DisableS3BucketPublicReadWrite exists in us-east-1
  - [PASS] Config service role has ssm:StartAutomationExecution permission
  - [PASS] 12 + 1 = 13 rules <= 150 limit
STEPS:
  1. CONFIRM: About to put-config-rule s3-bucket-public-read-prohibited in
     account 111111111111 region us-east-1. This will CREATE a new Config
     rule that detects S3 buckets with public read access, plus attach
     auto-remediation (AWS-DisableS3BucketPublicReadWrite). First evaluation
     in 1-30 min. Proceed? (yes/no)
  2. aws configservice put-config-rule --config-rule '{"ConfigRuleName":"s3-bucket-public-read-prohibited","Description":"Detects S3 buckets that allow public read access. Runbook: https://runbooks.example.com/s3-public","Source":{"Owner":"AWS","SourceIdentifier":"S3_BUCKET_PUBLIC_READ_PROHIBITED"},"Scope":{"ComplianceResourceTypes":["AWS::S3::Bucket"]},"ConfigRuleState":"ACTIVE"}'
  3. aws configservice put-remediation-configurations --remediation-configurations '[{"ConfigRuleName":"s3-bucket-public-read-prohibited","TargetType":"SSM_DOCUMENT","TargetId":"AWS-DisableS3BucketPublicReadWrite","Automatic":true,"MaximumAutomaticAttempts":3,"RetryAttemptSeconds":600,"Parameters":{"S3BucketName":{"ResourceValue":{"Value":"RESOURCE_ID"}}}}]'
  4. aws configservice start-config-rules-evaluation --config-rule-names s3-bucket-public-read-prohibited
POST_VERIFY:
  - (pending execution)
  - describe-config-rules returns rule with ConfigRuleState ACTIVE
  - get-compliance-summary shows Compliant:N / NonCompliant:N after first evaluation (~5 min)
  - describe-remediation-configurations returns the remediation with Automatic: true
EVALUATION: configuration-change:1-30min (forced via start-config-rules-evaluation)
COMPLIANCE: pending — first evaluation not complete
REMEDIATION: auto:AWS-DisableS3BucketPublicReadWrite (Automatic=true, max 3 attempts)
NOTES:
  - Evaluation mode: configuration-change triggered. Rule evaluates on S3
    bucket creation/update/delete.
  - Auto-remediation is ENABLED (Automatic: true). Non-compliant buckets
    will be automatically blocked from public access within minutes of
    detection. MaximumAutomaticAttempts: 3, RetryAttemptSeconds: 600.
  - To force immediate evaluation:
    aws configservice start-config-rules-evaluation --config-rule-names s3-bucket-public-read-prohibited
  - Security Hub integration: compliance results will appear as findings
    in Security Hub automatically (if Security Hub is enabled).
```

## Skill output — custom Lambda rule

```text
RULE: ec2-required-tags
VERDICT: READY_TO_DEPLOY
TARGET: ec2-required-tags
PRE_CHECKS:
  - [PASS] Configuration recorder active (recording = true)
  - [PASS] Delivery channel configured (S3 bucket: config-bucket-111111111111)
  - [PASS] Lambda function config-rule-required-tags exists (python3.12, timeout: 30s)
  - [PASS] Lambda resource-based policy allows config.amazonaws.com invocation
    (statement AllowConfigToInvoke, sourceAccount: 111111111111)
  - [PASS] Lambda IAM role config-rule-lambda-role has config:PutEvaluations
  - [PASS] Lambda timeout 30s <= 60s Config invocation limit
  - [PASS] Scope AWS::EC2::Instance is a supported resource type
  - [PASS] 13 + 1 = 14 rules <= 150 limit
STEPS:
  1. CONFIRM: About to put-config-rule ec2-required-tags in account
     111111111111 region us-east-1. This will CREATE a new custom Config
     rule that evaluates EC2 instances for required tags (Environment,
     Owner, CostCenter). First evaluation in 1-30 min. Proceed? (yes/no)
  2. aws configservice put-config-rule --config-rule '{"ConfigRuleName":"ec2-required-tags","Description":"Ensures all EC2 instances have Environment, Owner, and CostCenter tags","Source":{"Owner":"CUSTOM_LAMBDA","SourceIdentifier":"arn:aws:lambda:us-east-1:111111111111:function:config-rule-required-tags","SourceDetails":[{"EventSource":"aws.config","MessageType":"ConfigurationItemChangeNotification"}]},"Scope":{"ComplianceResourceTypes":["AWS::EC2::Instance"]},"InputParameters":"{\"requiredTags\":\"Environment,Owner,CostCenter\"}","ConfigRuleState":"ACTIVE"}'
  3. aws configservice start-config-rules-evaluation --config-rule-names ec2-required-tags
POST_VERIFY:
  - (pending execution)
  - describe-config-rules returns rule with ConfigRuleState ACTIVE
  - describe-config-rule-evaluation-status shows LastSuccessfulInvocationTime is recent
  - get-compliance-summary shows Compliant:N / NonCompliant:N after first evaluation
EVALUATION: configuration-change:1-30min (forced via start-config-rules-evaluation)
COMPLIANCE: pending — first evaluation not complete
REMEDIATION: none (compliance reporting only; add SSM doc for auto-tagging)
NOTES:
  - Custom Lambda rule: Config invokes the function on each EC2 instance
    change. The function checks for required tags and reports COMPLIANT or
    NON_COMPLIANT to Config via PutEvaluations.
  - Lambda permission for Config is configured (statement AllowConfigToInvoke).
    Without this, Config silently fails to invoke the function.
  - Lambda timeout is 30s — well within the 60s Config invocation limit.
    If the function needs more time, optimize the tag-checking logic.
  - Consider adding SSM Automation remediation (AWS-AttachEC2InstanceTags)
    to automatically add missing tags.
```

## Skill output — organization rule (PREREQUISITES_MISSING)

```text
RULE: org-s3-public-read-prohibited
VERDICT: PREREQUISITES_MISSING
TARGET: org-s3-public-read-prohibited
PRE_CHECKS:
  - [PASS] Configuration recorder active in member account 222222222222
  - [PASS] Delivery channel configured in member account
  - [FAIL] This account (222222222222) is a MEMBER account, not the
    organization management account (111111111111). Organization config
    rules can only be deployed from the management account or a delegated
    administrator. The put-organization-config-rule API will return
    AccessDeniedException.
  - [PASS] ManagedRuleIdentifier S3_BUCKET_PUBLIC_READ_PROHIBITED valid
STEPS: (none — pre-checks failed; deploy from management account)
POST_VERIFY: (none)
EVALUATION: (blocked)
COMPLIANCE: (blocked)
REMEDIATION: (blocked)
NOTES:
  - Root cause: organization config rules require management account
    authorization. The current account (222222222222) is a member, not
    the management account (111111111111).
  - Remediation: switch to the management account credentials and re-deploy:
    aws configservice put-organization-config-rule \
      --organization-config-rule '{
        "OrganizationConfigRuleName": "org-s3-public-read-prohibited",
        "OrganizationManagedRuleMetadata": {
          "RuleIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
          "ResourceTypesScope": ["AWS::S3::Bucket"]
        }
      }'
    --profile management-account
  - The rule will apply to ALL member accounts in the organization,
    including 222222222222.
  - Alternatively, delegate Config administration to a dedicated account
    via AWS Organizations: the delegated admin account can deploy org
    rules without management account credentials.
  - To check if delegated admin is configured:
    aws organizations list-delegated-administrators \
      --service-principal config-multiaccountsetup.amazonaws.com
```

## What the skill caught that a generic assistant misses

1. **Recorder status verification.** A generic assistant emits the
   put-config-rule command directly. The skill verifies the recorder is
   running first — a rule on a stopped recorder reports stale compliance
   indefinitely. This is the #1 Config blind spot.

2. **Remediation is NOT automatic by default.** A generic assistant
   attaches the SSM document and assumes auto-remediation. The skill
   explicitly sets `Automatic: true` and surfaces `MaximumAutomaticAttempts`
   and `RetryAttemptSeconds` — without these, remediation is manual.

3. **Lambda permission for Config.** A generic assistant creates the
   custom rule without checking the Lambda resource-based policy. The
   skill verifies the `config.amazonaws.com` invocation permission exists
   — without it, the rule silently reports EvaluationError for all
   resources.

4. **Evaluation lag awareness.** A generic assistant deploys and claims
   done. The skill surfaces that PutConfigRule does NOT trigger immediate
   evaluation — it takes 1-30 minutes (configuration-change) or up to
   MaximumExecutionFrequency (periodic). The skill includes
   `start-config-rules-evaluation` to force evaluation.

5. **Organization rule authorization.** A generic assistant emits the
   put-organization-config-rule from any account. The skill detects that
   the current account is a member, not the management account, and
   blocks deployment — preventing an AccessDeniedException that would
   confuse the operator.

6. **Conformance pack as CloudFormation.** A generic assistant treats
   conformance packs as simple API calls. The skill knows they deploy via
   CloudFormation under the hood — template errors surface as stack events,
   not Config API errors. The skill validates template syntax first.

7. **Stale compliance heuristic.** A generic assistant reports
   "Compliant" as good news. The skill includes a diagnostic decision tree
   for stale compliance: is the recorder running? is the last evaluation
   recent? did the Lambda error? Operators learn that "Compliant" can
   mean "nobody checked."

8. **CONFIRM gate.** A generic assistant auto-executes. The skill emits
   `CONFIRM:` and waits — put-config-rule overwrites the existing rule
   with no version history.

## Slash-command invocation

```
/aws:deploy-config-rule
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a config rule to detect public S3 buckets"
```

The orchestrator emits
`[Phase: Deploy | Skills routed: config-rule-deployer]` and hands off to
this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create a config rule"
# [Phase: Deploy | Skills routed: config-rule-deployer]
```

## Live-account follow-up (optional, requires AWS CLI)

After the rule is deployed:

```bash
# Verify the rule exists and is active
aws configservice describe-config-rules \
  --config-rule-names s3-bucket-public-read-prohibited \
  --profile default \
  --query 'ConfigRules[0].{Name:ConfigRuleName,State:ConfigRuleState,Source:Source.SourceIdentifier}'

# Check compliance summary (wait 5-30 min for first evaluation)
aws configservice get-compliance-summary \
  --config-rule-names s3-bucket-public-read-prohibited \
  --profile default

# List non-compliant resources
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name s3-bucket-public-read-prohibited \
  --compliance-types NON_COMPLIANT \
  --profile default

# Check remediation execution status
aws configservice describe-remediation-executions-status \
  --config-rule-name s3-bucket-public-read-prohibited \
  --profile default

# Verify the configuration recorder is still running
aws configservice describe-configuration-recorder-status \
  --profile default
```
