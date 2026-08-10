---
name: config-rule-deployer
description: >-
  Provisions AWS Config rules with compliance coverage: managed rules
  (100+ AWS-managed like s3-bucket-public-read-prohibited,
  iam-user-no-policies), custom Lambda rules, rule scope, evaluation
  mode (config-change vs periodic), compliance reporting, Security Hub
  integration, SSM Automation remediation, conformance packs (bulk
  deployment), organization config rules (org-wide), configuration
  recorder and delivery channel setup, and proactive rules (evaluate
  before deployment via CloudFormation hooks). Runs pre-checks
  (recorder status, delivery channel, IAM, Lambda function existence,
  SSM document existence), emits put-config-rule / put-conformance-pack
  / put-organization-config-rule CLI behind CONFIRM gate, verifies
  compliance evaluation. Emits READY_TO_DEPLOY | PREREQUISITES_MISSING.
  Use for security baselines (CIS, PCI-DSS), tagging enforcement,
  drift detection, or automated remediation.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws configservice put-config-rule, put-conformance-pack,
  put-organization-config-rule, describe-config-rules,
  describe-configuration-recorders, describe-delivery-channels,
  start-config-rules-evaluation, get-compliance-summary (AWS CLI v2,
  SSO or key-based credentials).
keywords:
  - AWS Config
  - config rules
  - managed rules
  - custom rules
  - Lambda evaluation
  - conformance packs
  - organization config rules
  - compliance
  - remediation
  - SSM Automation
  - Security Hub
  - configuration recorder
  - delivery channel
  - proactive rules
  - CloudFormation hooks
  - drift detection
  - CIS benchmark
  - PCI-DSS
  - tagging enforcement
  - put-config-rule
  - put-conformance-pack
tags: [aws-config, compliance, governance, deploy, config-rules, conformance-packs, remediation]
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws-config
    - compliance
    - governance
    - deploy
    - config-rules
    - conformance-packs
    - remediation
  dependencies:
    - aws-orchestrator
  keywords:
    - AWS Config
    - config rules
    - managed rules
    - conformance packs
    - remediation
    - compliance
  when_to_use: >-
    Creating AWS Config rules (managed, custom Lambda, organization-wide),
    deploying conformance packs for bulk compliance baselines (CIS, PCI-DSS,
    NIST), configuring SSM Automation remediation, integrating Config with
    Security Hub, setting up the configuration recorder and delivery channel,
    deploying proactive rules for CloudFormation pre-deployment evaluation,
    or auditing existing Config rule compliance coverage.
  activation_triggers:
    - "create config rule"
    - "deploy config rule"
    - "managed config rule"
    - "custom config rule"
    - "Lambda config rule"
    - "conformance pack"
    - "organization config rule"
    - "org config rule"
    - "config rule remediation"
    - "SSM Automation remediation"
    - "Security Hub integration"
    - "configuration recorder"
    - "delivery channel"
    - "proactive config rule"
    - "CloudFormation hooks"
    - "CIS benchmark config"
    - "PCI-DSS config rules"
    - "tagging enforcement rule"
    - "config compliance"
    - "put-config-rule"
  invocation_schema: >-
    Input: either (a) a rule deployment intent (create managed, create
    custom, deploy conformance pack, deploy org rule) with target rule
    name, managed rule identifier or Lambda function ARN, resource scope,
    evaluation mode, and optional remediation, OR (b) a rule name for
    live-account update or compliance validation. Output: deterministic
    RULE/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where
    VERDICT is one of READY_TO_DEPLOY, PREREQUISITES_MISSING.
---

# AWS Config Rule Deployer

## What this skill does

Provisions AWS Config rules with correct evaluation modes, resource
scopes, and remediation wiring. Runs deterministic pre-checks before any
state-changing CLI (is the configuration recorder running? does the
delivery channel exist? does the Lambda function exist for custom rules?
does the SSM Automation document exist for remediation? does the IAM
principal hold `config:PutConfigRule`?), emits the exact `put-config-rule`
/ `put-conformance-pack` / `put-organization-config-rule` CLI behind a
CONFIRM gate, and verifies compliance evaluation after apply. Every rule
plan surfaces the evaluation frequency (configuration-change triggered
vs periodic), the maximum evaluation frequency (1h/3h/6h/12h/24h), and
the remediation trigger model (automatic vs manual).

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority order + rule types | Before any operation |
| **§ Mindset** | Why recorder status matters, evaluation modes, remediation triggers | Understanding the compliance model |
| **§ Pre-flight** | Recorder/delivery channel/IAM gate — rule metadata | Before executing any CLI |
| **§ Process** | Per-operation planning: managed, custom, conformance, org, proactive | When choosing which operation |
| **§ Common patterns** | Managed rule / custom Lambda / conformance pack / remediation boilerplate | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, POST_VERIFY | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that cause non-compliant or broken rules | Review before deploy |
| **§ Pre-flight safety** | Additional checks before any provisioning CLI | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | One or more pre-checks failed (recorder stopped, delivery channel missing, Lambda function not found for custom rule, SSM document not found for remediation, IAM permission missing) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY_TO_DEPLOY):**

1. **Configuration recorder** — `describe-configuration-recorders` returns
   a recorder with `recordingGroup.allSupported = true` (or scoped resource
   types) and `status.recording = true`.
2. **Delivery channel** — `describe-delivery-channels` returns a channel
   with a valid S3 bucket that exists and accepts Config data.
3. **Rule type validation** — managed rule identifier exists in the AWS
   Config managed rules list; custom rule has a valid Lambda function ARN.
4. **Resource scope** — the rule's scope (resource types, resource IDs,
   tag key/value) is valid for the rule's evaluation type.
5. **Evaluation mode** — configuration-change-triggered rules have valid
   resource types; periodic rules have a valid MaximumExecutionFrequency
   (1h/3h/6h/12h/24h).
6. **IAM permissions** — the operator principal holds `config:PutConfigRule`
   and (for custom rules) `lambda:AddPermission` /
   `lambda:RemovePermission`.
7. **Lambda function policy** — for custom rules, the Lambda function has
   a permission statement allowing `config.amazonaws.com` to invoke it.
8. **SSM document** — for remediation, the referenced SSM Automation
   document exists and the Config service role has permission to assume it.
9. **Security Hub integration** — if forwarding compliance to Security
   Hub, verify Security Hub is enabled in the account/region.
10. **Organization aggregator** — for org config rules, verify the
    organization aggregator is authorized in the management account.

**Config rule limits (2026):**

- Max rules per region per account: 150 (soft limit, request increase).
- Max conformance packs per region per account: 25.
- Max organization config rules per region: 150.
- MaximumExecutionFrequency options: One_Hour, Three_Hours, Six_Hours,
  Twelve_Hours, TwentyFour_Hours.
- Config rule evaluation lag: 1-30 min for configuration-change rules;
  up to MaximumExecutionFrequency for periodic rules.
- Conformance pack template body max size: 256 KB.

## Mindset

**One-line takeaway:** a Config rule has one job — evaluate resource
compliance and optionally trigger remediation. When any link breaks
(recorder stopped, Lambda function deleted, SSM document missing), the
rule silently reports stale compliance — operators see "Compliant" when
the rule hasn't actually evaluated anything. Driven by three AWS Config
realities:

- **The configuration recorder is the foundation.** If the recorder is
  stopped or the delivery channel is broken, ALL rules report stale
  compliance. A rule deployed against a stopped recorder evaluates
  nothing — it shows the last-known state indefinitely. This is the #1
  Config blind spot: operators deploy rules and assume compliance is
  fresh, but the recorder has been off for weeks.

- **Config rules evaluate asynchronously.** After `put-config-rule`, the
  rule does NOT evaluate immediately. Configuration-change rules evaluate
  on the next resource change; periodic rules evaluate at the next
  MaximumExecutionFrequency interval. To force immediate evaluation, run
  `start-config-rules-evaluation --config-rule-names <name>`. Even then,
  the evaluation takes 1-30 minutes depending on resource volume.

- **Remediation requires explicit opt-in.** Adding an SSM Automation
  document to a Config rule does NOT automatically remediate non-compliant
  resources. Each non-compliant resource must be remediated via
  `start-remediation-execution` (manual trigger) or the rule must be
  configured with `AutoRemediation = true` for automatic remediation.
  Operators frequently deploy rules with remediation documents and assume
  auto-remediation is active — it isn't.

## Pre-flight: Config rule metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws configservice describe-configuration-recorders` — confirm a
   recorder exists and `status.recording = true`. Capture
   `recordingGroup` to verify the rule's resource types are in scope.
2. `aws configservice describe-delivery-channels` — confirm the delivery
   channel has a valid `s3BucketName` and the bucket exists.
3. `aws configservice describe-config-rules --config-rule-names <name>`
   — confirm the rule exists (or doesn't, for create ops). Capture
   `ConfigRuleState`, `Source`, `Scope`, `MaximumExecutionFrequency`.
4. For managed rules: verify the `ManagedRuleIdentifier` is valid in the
   AWS Config managed rules list.
5. For custom rules: `aws lambda get-function --function-name <name>` —
   verify the Lambda function exists and has a permission statement for
   `config.amazonaws.com`.
6. For remediation: `aws ssm describe-document --name <document-name>`
   — verify the SSM Automation document exists.
7. For conformance packs: `aws configservice describe-conformance-packs`
   — check for naming conflicts.
8. For org rules: `aws organizations describe-organization` — verify
   the account is the management account or a delegated admin.

**Malformed input:** if the rule configuration is invalid or missing
required fields, emit `VERDICT: PREREQUISITES_MISSING` with `REASON:
Rule configuration is not valid or is missing required fields — cannot
plan.` and `REMEDIATION: Verify the rule definition against the AWS Config
API reference at https://docs.aws.amazon.com/config/latest/APIReference/.`

| Attribute | Effect on operation |
|---|---|
| Recorder stopped (`status.recording = false`) | ALL rules report stale compliance. Must start recorder first. PREREQUISITES_MISSING. |
| Delivery channel missing or S3 bucket deleted | Config cannot store configurations. PREREQUISITES_MISSING. |
| `ConfigRuleState: DELETING` | Rule is being deleted. Wait for completion before recreating. |
| Lambda function for custom rule not found | Custom rule has nothing to invoke. PREREQUISITES_MISSING. |
| Lambda permission for Config missing | Config cannot invoke the function. Rule will report evaluation errors. |
| SSM document for remediation not found | Remediation cannot execute. Rule reports compliance but cannot auto-fix. |
| Organization aggregator not authorized | Org rules cannot aggregate compliance. PREREQUISITES_MISSING. |
| Rule scope includes unsupported resource type | Rule accepts the config but evaluates nothing. Silent blind spot. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious AWS Config behaviors

These behaviors are easy to misjudge without operational Config
experience. Each changes a plan if ignored:

- **The configuration recorder must be RUNNING.** If
  `status.recording = false`, every Config rule in the account reports
  stale compliance from the last time the recorder was active. This is
  the single most common Config blind spot: operators deploy rules and
  assume compliance data is fresh, but the recorder was stopped months
  ago (often to save costs) and never restarted.

- **PutConfigRule does NOT trigger immediate evaluation.** After
  creating a rule, it evaluates on the next resource change (for
  configuration-change rules) or at the next MaximumExecutionFrequency
  interval (for periodic rules). To force evaluation:
  `aws configservice start-config-rules-evaluation --config-rule-names
  <name>`. Even forced evaluation takes 1-30 minutes.

- **Remediation is NOT automatic by default.** Adding an SSM Automation
  document as a remediation configuration does NOT auto-remediate. Each
  non-compliant resource needs `start-remediation-execution` (manual) or
  the remediation must have `AutoRemediation = true`. The default is
  manual — operators frequently assume auto-remediation is active.

- **MaximumExecutionFrequency applies to BOTH periodic AND
  configuration-change rules.** For periodic rules, it controls how often
  the rule evaluates. For configuration-change rules, it controls how
  often Config re-evaluates resources that have NOT changed (periodic
  re-evaluation of existing resources). The default is 24 hours.

- **Config rules have a 150-per-region soft limit.** Large enterprises
  with CIS + PCI-DSS + NIST conformance packs can easily exceed this.
  Request a limit increase via AWS Support before deploying large packs.

- **Conformance packs deploy via CloudFormation under the hood.** A
  conformance pack creates a CloudFormation stack in the Config service
  account. Stack creation takes 2-10 minutes. Errors in the template
  surface as CloudFormation stack events, not Config API errors.

- **Organization config rules deploy from the management account (or
  delegated admin).** The rule applies to ALL member accounts in the
  organization. Member accounts CANNOT modify or delete org rules — they
  are read-only compliance controls.

- **Custom rules invoke Lambda synchronously.** Config calls the Lambda
  function and waits for a response. If the Lambda times out (> 60s) or
  errors, the rule reports `EvaluationError` for that resource. Lambda
  functions for Config rules should be fast (< 10s) and idempotent.

- **Lambda permissions for Config are role-based, not resource-based.**
  The Lambda function needs a resource-based permission statement allowing
  `config.amazonaws.com` to invoke it. Without this, Config silently fails
  to invoke the function and the rule reports evaluation errors.

- **Security Hub imports Config compliance findings automatically.** When
  Security Hub is enabled, Config rule compliance results appear as
  findings in Security Hub. This integration is automatic — no additional
  configuration needed. But disabling Security Hub does NOT remove
  historical Config findings from the Config console.

- **Proactive rules (CloudFormation hooks) evaluate BEFORE resource
  creation.** Proactive rules use CloudFormation hooks to evaluate
  resource configurations before CloudFormation creates them. This
  prevents non-compliant resources from being deployed in the first place
  — unlike standard Config rules which evaluate after creation and
  report non-compliance retroactively.

- **Config rule scope narrows evaluation.** A scope of
  `resourceTypes: ["AWS::S3::Bucket"]` evaluates only S3 buckets. Without
  a scope, the rule evaluates ALL supported resource types — potentially
  exceeding evaluation timeouts and Lambda cost for custom rules.

- **Tag-based scope filters by resource tags.** A scope of
  `tagKey: "Environment", tagValue: "prod"` evaluates only resources
  tagged `Environment=prod`. Useful for phased compliance rollouts
  (start with prod, expand to all).

- **SSM Automation documents for remediation must be in the SAME
  region.** Cross-region remediation documents are not supported. The
  document must exist in each region where the Config rule is deployed.

- **Config API calls cost money.** Each `put-config-rule` and
  `start-config-rules-evaluation` is a billable API call. For large
  fleets (100+ rules, frequent evaluations), Config costs can exceed
  $1,000/month. Conformance packs with many rules amplify this.

- **Deletion is eventual.** `delete-config-rule` marks the rule for
  deletion but the rule may take up to 6 hours to fully delete. During
  this window, the rule continues to evaluate. `ConfigRuleState` shows
  `DELETING`.

### Step 1: Pre-check gate — PREREQUISITES_MISSING if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is
PREREQUISITES_MISSING with the failed checks enumerated in PRE_CHECKS.
Do NOT execute.

**For ALL operations:**
1. The configuration recorder exists and `status.recording = true`.
2. The delivery channel exists and references a valid S3 bucket.
3. The rule name is <= 128 chars, matches `^[a-zA-Z0-9-]+$`.
4. The IAM principal holds `config:PutConfigRule` (and
   `config:PutConformancePack` or
   `config:PutOrganizationConfigRule` as appropriate).
5. Total rule count + new rule <= 150 per region (soft limit).

**For managed rule (`Source.Owner: AWS`):**
6. The `ManagedRuleIdentifier` exists in the AWS Config managed rules
   list (e.g., `S3_BUCKET_PUBLIC_READ_PROHIBITED`,
   `IAM_USER_NO_POLICIES`).
7. The `Source.SourceIdentifier` matches the managed rule identifier.
8. Required input parameters for the managed rule are provided (varies
   by rule — e.g., `vpcId` for some VPC rules).

**For custom Lambda rule (`Source.Owner: CUSTOM_LAMBDA`):**
6. The Lambda function ARN exists (`lambda:get-function`).
7. The Lambda function has a resource-based permission statement
   allowing `config.amazonaws.com` to invoke it.
8. The Lambda function IAM role has `config:PutEvaluations` permission
   (to report compliance results back to Config).
9. The Lambda function timeout is <= 60s (Config invocation limit).

**For conformance pack:**
6. The conformance pack template body (or S3 template URL) is valid
   YAML/JSON with at least one rule definition.
7. The template body is <= 256 KB.
8. All managed rules referenced in the template have valid identifiers.
9. Total conformance pack count + new pack <= 25 per region.

**For organization config rule:**
6. The account is the organization management account or a delegated
   administrator.
7. The organization aggregator is authorized.
8. The `OrganizationCustomRuleMetadata` or
   `OrganizationManagedRuleMetadata` is complete.
9. The `ExcludedAccounts` list contains valid account IDs (or is empty).

**For remediation:**
10. The SSM Automation document exists in the same region
    (`ssm:describe-document`).
11. The Config service-linked role has `ssm:StartAutomationExecution`
    permission.
12. The remediation parameters match the SSM document's expected input.
13. `AutoRemediation = true` is an explicit choice — not the default.

### Step 2: READY_TO_DEPLOY — emit deployment plan

If all pre-checks pass, emit `VERDICT: READY_TO_DEPLOY` with the exact
CLI sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated.
- The expected evaluation lag (configuration-change: 1-30 min; periodic:
  up to MaximumExecutionFrequency).
- The expected compliance status after first evaluation (initially
  `Compliant` or `NonCompliant` based on current resource state).
- The remediation behavior (automatic vs manual).
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`put-config-rule`, `put-conformance-pack`,
  `put-organization-config-rule`, `delete-config-rule`,
  `delete-conformance-pack`, `delete-organization-config-rule`),
  emit: `CONFIRM: About to <operation> on Config rule <name> in account
  <account> region <region>. This will <consequence>. Proceed? (yes/no)`.
  Do NOT execute until the operator confirms.
- Snapshot the current rule config before modification:
  `aws configservice describe-config-rules --config-rule-names <name>
  --output json > /tmp/<name>-backup-$(date +%s).json`.
- Execute the CLI.
- Force immediate evaluation:
  `aws configservice start-config-rules-evaluation --config-rule-names
  <name>`.

### Step 4: Post-verification

After the operation finishes, run post-verification:

1. `describe-config-rules --config-rule-names <name>` returns the
   expected rule configuration.
2. `get-compliance-summary --config-rule-names <name>` shows
   `Compliant` and `NonCompliant` resource counts (may take 1-30 min
   for the first evaluation).
3. For custom rules: `describe-config-rule-evaluation-status
   --config-rule-names <name>` shows `LastSuccessfulInvocationTime` is
   recent (not null).
4. For remediation: `describe-remediation-executions-status
   --config-rule-name <name>` shows remediation executions if
   non-compliant resources exist.
5. For conformance packs: `describe-conformance-pack-compliance
   --conformance-pack-name <name>` shows overall pack compliance.

## Common Config rule patterns (boilerplate)

### Managed rule — S3 public read prohibited

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Description": "Detects S3 buckets that allow public read access. Runbook: https://runbooks.example.com/s3-public",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"
    },
    "Scope": {
      "ComplianceResourceTypes": ["AWS::S3::Bucket"]
    },
    "ConfigRuleState": "ACTIVE"
  }'
```

### Managed rule — IAM user no policies (with input parameters)

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "iam-user-no-policies",
    "Description": "Ensures IAM users have no inline or managed policies directly attached. Use groups instead.",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "IAM_USER_NO_POLICIES"
    },
    "Scope": {
      "ComplianceResourceTypes": ["AWS::IAM::User"]
    },
    "InputParameters": "{\"policyScope\": \"All\"}",
    "ConfigRuleState": "ACTIVE"
  }'
```

### Managed rule with remediation (SSM Automation)

```bash
# 1. Create the rule
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"
    },
    "Scope": {
      "ComplianceResourceTypes": ["AWS::S3::Bucket"]
    }
  }'

# 2. Attach remediation (auto-remediate using SSM document AWS-DisableS3BucketPublicReadWrite)
aws configservice put-remediation-configurations \
  --remediation-configurations '[
    {
      "ConfigRuleName": "s3-bucket-public-read-prohibited",
      "TargetType": "SSM_DOCUMENT",
      "TargetId": "AWS-DisableS3BucketPublicReadWrite",
      "Automatic": true,
      "MaximumAutomaticAttempts": 3,
      "RetryAttemptSeconds": 600,
      "Parameters": {
        "S3BucketName": {
          "ResourceValue": {
            "Value": "RESOURCE_ID"
          }
        }
      }
    }
  ]'
```

### Custom Lambda rule — tag enforcement

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "ec2-required-tags",
    "Description": "Ensures all EC2 instances have Environment, Owner, and CostCenter tags.",
    "Source": {
      "Owner": "CUSTOM_LAMBDA",
      "SourceIdentifier": "arn:aws:lambda:us-east-1:111111111111:function:config-rule-required-tags",
      "SourceDetails": [
        {
          "EventSource": "aws.config",
          "MessageType": "ConfigurationItemChangeNotification"
        }
      ]
    },
    "Scope": {
      "ComplianceResourceTypes": ["AWS::EC2::Instance"]
    },
    "InputParameters": "{\"requiredTags\": \"Environment,Owner,CostCenter\"}",
    "ConfigRuleState": "ACTIVE"
  }'
```

**Lambda permission for Config invocation (REQUIRED):**
```bash
aws lambda add-permission \
  --function-name config-rule-required-tags \
  --statement-id AllowConfigToInvoke \
  --action lambda:InvokeFunction \
  --principal config.amazonaws.com \
  --source-account 111111111111
```

### Periodic rule — evaluate every 6 hours

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "iam-password-policy-check",
    "Description": "Checks the account password policy meets minimum requirements. Evaluates every 6 hours.",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "IAM_PASSWORD_POLICY"
    },
    "MaximumExecutionFrequency": "Six_Hours",
    "ConfigRuleState": "ACTIVE"
  }'
```

Note: account-level rules (not scoped to a resource type) MUST be periodic
because there is no resource change to trigger evaluation.

### Conformance pack — CIS AWS Foundations Benchmark

```bash
aws configservice put-conformance-pack \
  --conformance-pack-name "cis-aws-foundations-benchmark" \
  --conformance-pack-input-parameters \
    ParameterKey=ConformancePackName,ParameterValue=cis-aws-foundations-benchmark \
  --template-body '
Resources:
  IamNoInlinePolicyRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: iam-no-inline-policy
      Source:
        Owner: AWS
        SourceIdentifier: IAM_NO_INLINE_POLICY_CHECK
      Scope:
        ComplianceResourceTypes: ["AWS::IAM::User"]
  IamPasswordPolicyRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: iam-password-policy
      Source:
        Owner: AWS
        SourceIdentifier: IAM_PASSWORD_POLICY
      MaximumExecutionFrequency: Six_Hours
  RootMfaEnabledRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: root-mfa-enabled
      Source:
        Owner: AWS
        SourceIdentifier: ROOT_ACCOUNT_MFA_ENABLED
      MaximumExecutionFrequency: One_Hour
'
```

### Organization config rule — org-wide managed rule

```bash
aws configservice put-organization-config-rule \
  --organization-config-rule '{
    "OrganizationConfigRuleName": "org-s3-public-read-prohibited",
    "OrganizationManagedRuleMetadata": {
      "Description": "Org-wide: no S3 buckets with public read access.",
      "RuleIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
      "InputParameters": "{}",
      "ResourceTypesScope": ["AWS::S3::Bucket"]
    },
    "ExcludedAccounts": [],
    "OrganizationCustomRuleMetadata": null
  }'
```

### Proactive rule (CloudFormation hook)

```bash
aws cloudformation register-type \
  --type-name CfnHook::Config::ProactiveRule \
  --type-resource-type HOOK \
  --schema-handler-package s3://my-bucket/proactive-rule-hook.zip

aws cloudfoundation set-type-default-version \
  --type-name CfnHook::Config::ProactiveRule \
  --version-id 1

# Create a CloudFormation stack with the hook to block non-compliant S3 bucket creation
aws cloudformation create-stack \
  --stack-name proactive-s3-public-read-block \
  --template-body '
Resources:
  ProactiveS3Hook:
    Type: CfnHook::Config::ProactiveRule
    Properties:
      RuleIdentifier: S3_BUCKET_PUBLIC_READ_PROHIBITED
      ResourceTypes: ["AWS::S3::Bucket"]
      TargetOperations: ["CREATE", "UPDATE"]
'
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
RULE: <rule-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <rule-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> on Config rule <name> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
EVALUATION: <configuration-change:1-30min | periodic:Next_MaxFreq | pending>
COMPLIANCE: <Compliant:N / NonCompliant:N / pending — first evaluation not complete>
REMEDIATION: <none | manual:SSM-doc | auto:SSM-doc>
NOTES: <evaluation mode rationale, remediation trigger model, recorder status caveat>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll deploy…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING` (not `ready`, `prerequisites`).
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]`
  or `[FAIL]` and a specific reason for each failure. An empty
  PRE_CHECKS block is non-compliant.
- NEVER deploy a rule without verifying the configuration recorder is
  RUNNING. A rule on a stopped recorder reports stale compliance — the
  #1 Config blind spot.
- NEVER emit a CLI command with placeholder flags (e.g.,
  `"ConfigRuleName": "<name>"`) in a READY_TO_DEPLOY plan — every field
  must be populated with actual values from the input data.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation.
- NEVER claim auto-remediation is active when `Automatic` is not
  explicitly set to `true` in the remediation configuration. The default
  is manual remediation.
- NEVER deploy a custom Lambda rule without verifying the Lambda
  permission for `config.amazonaws.com` exists. Without it, Config
  silently fails to invoke the function.
- NEVER deploy a periodic rule without specifying
  MaximumExecutionFrequency — the default (24h) may be too slow for
  security-critical checks.

### Perfect example output

```text
RULE: s3-bucket-public-read-prohibited
VERDICT: READY_TO_DEPLOY
TARGET: s3-bucket-public-read-prohibited
PRE_CHECKS:
  - [PASS] Configuration recorder active (recording = true, allSupported = true)
  - [PASS] Delivery channel configured (S3 bucket: config-bucket-111111111111)
  - [PASS] ManagedRuleIdentifier S3_BUCKET_PUBLIC_READ_PROHIBITED valid
  - [PASS] Scope AWS::S3::Bucket is a supported resource type
  - [PASS] Rule is configuration-change triggered (no MaximumExecutionFrequency needed)
  - [PASS] IAM principal holds config:PutConfigRule
  - [PASS] Rule count 12 + 1 = 13 <= 150 limit
STEPS:
  1. CONFIRM: About to put-config-rule s3-bucket-public-read-prohibited in account 111111111111 region us-east-1. This will CREATE a new Config rule that detects S3 buckets allowing public read access. First evaluation in 1-30 min. Proceed? (yes/no)
  2. aws configservice put-config-rule --config-rule '{"ConfigRuleName":"s3-bucket-public-read-prohibited","Description":"Detects S3 buckets that allow public read access","Source":{"Owner":"AWS","SourceIdentifier":"S3_BUCKET_PUBLIC_READ_PROHIBITED"},"Scope":{"ComplianceResourceTypes":["AWS::S3::Bucket"]},"ConfigRuleState":"ACTIVE"}'
POST_VERIFY:
  - (pending execution)
  - describe-config-rules returns the rule with ConfigRuleState ACTIVE
  - get-compliance-summary shows Compliant:42 / NonCompliant:0 (after first evaluation, ~5 min)
EVALUATION: configuration-change:1-30min (will force via start-config-rules-evaluation)
COMPLIANCE: pending — first evaluation not complete
REMEDIATION: none (compliance reporting only)
NOTES:
  - Evaluation mode: configuration-change triggered. The rule evaluates
    on S3 bucket creation/update/delete. MaximumExecutionFrequency
    controls periodic re-evaluation of unchanged resources (default 24h).
  - To force immediate evaluation:
    aws configservice start-config-rules-evaluation --config-rule-names s3-bucket-public-read-prohibited
  - Consider attaching remediation (AWS-DisableS3BucketPublicReadWrite SSM
    document) for automatic public access blocking.
```

## Anti-Patterns — NEVER do these things

- NEVER deploy a Config rule without first verifying the configuration
  recorder is running. A stopped recorder means ALL rules report stale
  compliance — the rule appears active but evaluates nothing.

- NEVER assume `put-config-rule` triggers immediate evaluation. The rule
  evaluates on the next resource change (configuration-change rules) or
  at the next MaximumExecutionFrequency interval (periodic rules). Always
  run `start-config-rules-evaluation` after creating a rule.

- NEVER assume remediation is automatic. Adding an SSM Automation document
  does NOT auto-remediate unless `Automatic: true` is explicitly set.
  The default is manual — operators must trigger remediation via
  `start-remediation-execution`.

- NEVER deploy a custom Lambda rule without verifying the Lambda resource-
  based permission for `config.amazonaws.com`. Without this permission,
  Config silently fails to invoke the function and the rule reports
  evaluation errors for every resource.

- NEVER deploy a custom Lambda rule where the function timeout exceeds 60
  seconds. Config's Lambda invocation has a hard 60s timeout. A function
  that takes longer reports `EvaluationError` for every resource.

- NEVER use a Config rule scope that includes unsupported resource types.
  The rule accepts the configuration but evaluates nothing — a silent
  blind spot. Verify resource type support in the managed rule
  documentation.

- NEVER exceed 150 Config rules per region without requesting a limit
  increase. The 151st rule is silently rejected. For large compliance
  programs, use conformance packs (which bundle rules but still count
  toward the 150 limit).

- NEVER deploy a conformance pack with an invalid template body. The
  CloudFormation stack creation fails silently — Config reports the pack
  as CREATE_IN_PROGRESS indefinitely. Always validate the template YAML
  before deployment.

- NEVER assume Security Hub integration is bi-directional. Config forwards
  compliance findings TO Security Hub automatically. But remediating or
  suppressing a finding in Security Hub does NOT change the Config rule
  compliance status. They are separate systems.

- NEVER delete a Config rule to "stop noise" without first understanding
  why resources are non-compliant. The correct first step is to set
  `ConfigRuleState: INACTIVE` (via delete + recreate, or by removing the
  rule from the conformance pack) while investigating.

- NEVER forget the SSM Automation document must be in the SAME region as
  the Config rule. Cross-region remediation documents are not supported.
  For multi-region compliance, deploy the document in each region.

- NEVER auto-execute a state-changing Config CLI without the CONFIRM
  gate. `put-config-rule` overwrites the existing rule with no version
  history. `delete-config-rule` is irreversible (recreate from snapshot).

- NEVER deploy an organization config rule from a member account. Org
  rules must be deployed from the management account or a delegated
  administrator. Member accounts lack the `organizations:ListAccounts`
  permission needed for org-wide rule evaluation.

- NEVER use periodic evaluation for security-critical rules when
  configuration-change evaluation is available. Periodic rules evaluate
  at MaximumExecutionFrequency intervals — a non-compliant resource can
  exist for up to 24 hours before detection. Configuration-change rules
  evaluate within minutes of a resource change.

- NEVER deploy proactive rules without testing the CloudFormation hook
  behavior first. A misconfigured hook can block ALL CloudFormation
  deployments in the account — including infrastructure that on-call
  teams need for incident response. Test in a non-production account.

## Pre-flight safety checks (run before any provisioning CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-config-rule`, `put-conformance-pack`,
  `put-organization-config-rule`, `delete-config-rule`), the operator
  MUST emit: `CONFIRM: About to <action> on Config rule <name> in
  account <account> region <region>. This affects <consequence>.
  Proceed? (yes/no)`. Do NOT execute until the operator confirms.

- **PutConfigRule overwrites the entire rule configuration.** Always
  snapshot before modification:
  `aws configservice describe-config-rules --config-rule-names <name>
  --output json > /tmp/<name>-backup-$(date +%s).json`.

- For custom Lambda rules, verify the function's resource-based policy
  includes a permission statement for `config.amazonaws.com`. Missing
  this permission is the #1 cause of custom rule evaluation errors.

- For remediation configurations, verify the SSM Automation document
  exists AND the Config service-linked role has
  `ssm:StartAutomationExecution` permission. A missing document or role
  causes remediation to fail silently.

- For conformance packs, the template body is a CloudFormation template.
  Validate the YAML syntax and resource definitions before deployment.
  Template errors surface as CloudFormation stack events, not Config
  API errors.

- For organization config rules, verify the management account has
  authorized the Config service as a delegated administrator (if using
  delegated admin mode). Without authorization, org rules cannot
  aggregate compliance.

- Prefer configuration-change rules over periodic rules for security-
  critical checks. Configuration-change rules detect non-compliance
  within minutes; periodic rules can take up to 24 hours.

## Expert heuristic: stale compliance vs real compliance

A Config rule showing "Compliant" does NOT mean "all resources are
compliant right now." It means **the rule's most recent evaluation found
the resources compliant** — which may have been hours, days, or weeks
ago if the recorder is stopped or the rule hasn't evaluated recently.

**Diagnostic decision tree:**

```
Rule shows "Compliant" for all resources
   ├─ Is the configuration recorder running?
   │    ├─ NO → Stale compliance — restart recorder, force evaluation
   │    └─ YES → Check last evaluation time
   │              ├─ LastSuccessfulInvocationTime is old (> MaximumExecutionFrequency)?
   │              │    ├─ YES → Stale — force start-config-rules-evaluation
   │              │    └─ NO → Likely real compliance
   │              └─ For custom rules: Lambda had errors?
   │                   ├─ Check describe-config-rule-evaluation-status
   │                   └─ Check CloudWatch Logs for the Lambda function
   │
   └─ Confirm via get-compliance-details-by-config-rule:
        aws configservice get-compliance-details-by-config-rule \
          --config-rule-name <name>
        If empty result → no evaluations performed (stale or broken)
```

**Per-rule-type staleness indicators:**

| Rule type | What to check when compliance looks stale |
|---|---|
| Managed rule | Recorder running? `describe-configuration-recorder-status`. Rule in ACTIVE state? |
| Custom Lambda rule | Lambda function exists? Permission for Config? Last invocation had errors? Check CloudWatch Logs. |
| Periodic rule | MaximumExecutionFrequency elapsed since last evaluation? Force evaluation. |
| Conformance pack | CloudFormation stack status = CREATE_COMPLETE? Any stack drift? |
| Org rule | Management account permissions intact? Aggregator authorized? |

**Fix — verify and force fresh evaluation:**
1. `describe-configuration-recorder-status` — if `recording: false`,
   start it: `start-configuration-recorder`.
2. `describe-config-rule-evaluation-status --config-rule-names <name>`
   — check `LastSuccessfulInvocationTime`.
3. Force evaluation:
   `start-config-rules-evaluation --config-rule-names <name>`.
4. Wait 1-30 minutes, then re-check compliance.

ALWAYS pair Config rule deployment with a recorder status check. A
correctly configured rule on a stopped recorder is a false sense of
security.

## Recent AWS features (2024-2026)

- **Proactive Config rules (2024-2025):** evaluate CloudFormation
  templates BEFORE resource creation via CloudFormation hooks. Prevents
  non-compliant resources from being deployed in the first place — a
  shift from detective (post-creation) to preventive (pre-creation)
  compliance.
- **Conformance pack templates from Git repositories (2024):** deploy
  conformance packs directly from a Git repository (GitHub, CodeCommit)
  without uploading template bodies. Enables version-controlled
  compliance-as-code workflows.
- **Organization conformance packs (2024-2025):** deploy conformance
  packs across an entire organization from the management account. Bulk
  compliance baseline for all member accounts with a single API call.
- **Config rule coverage for 300+ resource types (2025):** expanded
  resource type support including newer services (AppRunner, Cedar
  policies, Bedrock guardrails). Verify coverage before deploying rules
  for exotic resource types.
- **Security Hub automated response (2025):** Security Hub can now
  trigger SSM Automation directly from Config findings without a custom
  Lambda intermediary. Reduces remediation latency from minutes to
  seconds.
- **Config data export to S3 with Parquet format (2024):** configuration
  snapshots and compliance history exported in Parquet format for
  Athena querying. Enables long-term compliance analytics and trend
  analysis.
- **Resource aggregation across regions (2024-2025):** improved
  multi-region aggregation with lower latency. Cross-region compliance
  dashboards refresh within minutes instead of hours.

## AWS documentation

- **AWS Config Developer Guide** — https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html
- **AWS Config Managed Rules** — https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html
- **Custom Lambda Rules** — https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_develop-rules_lambda-functions.html
- **Conformance Packs** — https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html
- **Organization Config Rules** — https://docs.aws.amazon.com/config/latest/developerguide/organization-config-rules-overview.html
- **Remediation (SSM Automation)** — https://docs.aws.amazon.com/config/latest/developerguide/remediation.html
- **Proactive Rules (CloudFormation Hooks)** — https://docs.aws.amazon.com/config/latest/developerguide/proactive-rules.html
- **AWS Config API Reference** — https://docs.aws.amazon.com/config/latest/APIReference/

## Domain

AWS CloudOps / Config Rule Provisioning, Compliance Automation & Governance.
