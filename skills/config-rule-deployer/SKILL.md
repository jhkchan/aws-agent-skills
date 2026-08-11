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
| **§ Quick reference** | Verdict thresholds + pre-check priority order | Before any operation |
| **§ Mindset** | Why recorder status matters, evaluation modes, remediation triggers | Understanding the model |
| **§ Pre-flight** | Recorder/delivery channel/IAM gate | Before executing any CLI |
| **§ Process** | Per-operation planning: managed, custom, conformance, org, proactive | When choosing which operation |
| **§ Common patterns** | Managed/custom/conformance/remediation boilerplate | Boilerplate lookup |
| **§ Output format** | STRICT output contract with worked example | Formatting the response |
| **§ NEVER** | Top 5 anti-patterns | Review before deploy |
| `references/` | Full NEVER list, stale compliance diagnostics, expert heuristics, all pattern examples | Deep reference |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | One or more pre-checks failed (recorder stopped, delivery channel missing, Lambda not found, SSM doc not found, IAM missing) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |

**Priority order for pre-checks (all must pass for READY_TO_DEPLOY):**

1. **Configuration recorder** — `recording = true`, `allSupported = true`
   (or scoped types).
2. **Delivery channel** — valid S3 bucket exists and accepts Config data.
3. **Rule type validation** — managed rule identifier exists; custom rule
   has valid Lambda ARN.
4. **Resource scope** — valid for the rule's evaluation type.
5. **Evaluation mode** — config-change has valid resource types; periodic
   has valid MaximumExecutionFrequency (1h/3h/6h/12h/24h).
6. **IAM permissions** — caller holds `config:PutConfigRule` and (for
   custom rules) `lambda:AddPermission`.
7. **Lambda function policy** — for custom rules, `config.amazonaws.com`
   can invoke the function.
8. **SSM document** — for remediation, document exists in-region and
   Config service role can assume it.
9. **Security Hub** — if forwarding compliance, verify SH is enabled.
10. **Organization aggregator** — for org rules, verify authorization.

**Config rule limits (2026):** max 150 rules/region/account (soft limit),
25 conformance packs/region, 150 org config rules/region. Template body
max 256 KB.

## Mindset

A Config rule has one job — evaluate resource compliance and optionally
trigger remediation. When any link breaks, the rule silently reports stale
compliance. Three AWS Config realities drive the mindset:

- **The configuration recorder is the foundation.** If stopped or the
  delivery channel is broken, ALL rules report stale compliance. #1 Config
  blind spot: rules appear active but evaluate nothing.
- **Config rules evaluate asynchronously.** After `put-config-rule`, the
  rule does NOT evaluate immediately. Force with
  `start-config-rules-evaluation`. Even then, 1-30 min lag.
- **Remediation requires explicit opt-in.** Adding an SSM Automation
  document does NOT auto-remediate. Each non-compliant resource needs
  `start-remediation-execution` (manual) or `AutoRemediation = true`.
  Operators frequently deploy rules with remediation documents and assume
  auto-remediation is active — it isn't.

## Pre-flight: Config rule metadata gate

Run before classification. **Live-account pre-flight:**

1. `aws configservice describe-configuration-recorders` — confirm
   `status.recording = true`. Capture `recordingGroup`.
2. `aws configservice describe-delivery-channels` — confirm valid S3 bucket.
3. `aws configservice describe-config-rules --config-rule-names <name>`
   — confirm rule exists (or doesn't). Capture state, source, scope.
4. For managed rules: verify `ManagedRuleIdentifier` is valid.
5. For custom rules: `aws lambda get-function` — verify function + permission
   for `config.amazonaws.com`.
6. For remediation: `aws ssm describe-document` — verify SSM doc exists.
7. For org rules: `aws organizations describe-organization` — verify
   management account or delegated admin.

| Attribute | Effect on operation |
|---|---|
| Recorder stopped | ALL rules report stale compliance. PREREQUISITES_MISSING. |
| Delivery channel missing/bucket deleted | Config cannot store data. PREREQUISITES_MISSING. |
| `ConfigRuleState: DELETING` | Wait for completion before recreating. |
| Lambda function not found | Custom rule has nothing to invoke. PREREQUISITES_MISSING. |
| SSM document not found | Remediation cannot execute. Reports compliance only. |
| Rule scope includes unsupported type | Rule evaluates nothing — silent blind spot. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious AWS Config behaviors

Key behaviors that change a plan if ignored (full detail in `references/`):

- **Recorder must be RUNNING.** Stopped recorder = stale compliance for ALL
  rules. Most common Config blind spot.
- **PutConfigRule does NOT trigger immediate evaluation.** Force with
  `start-config-rules-evaluation`. Even forced, takes 1-30 min.
- **Remediation is NOT automatic by default.** Must set `Automatic: true`
  explicitly. Default is manual.
- **MaximumExecutionFrequency applies to BOTH periodic AND config-change
  rules** (controls re-evaluation of unchanged resources for the latter).
- **Conformance packs deploy via CloudFormation under the hood.** Template
  errors surface as CFN stack events, not Config API errors.
- **Organization config rules deploy from management account only.** Member
  accounts cannot modify or delete org rules.
- **Custom rules invoke Lambda synchronously.** Lambda timeout > 60s or
  errors → `EvaluationError`. Keep functions < 10s and idempotent.
- **Lambda permissions for Config are resource-based.** Function needs a
  permission statement allowing `config.amazonaws.com` to invoke.
- **Proactive rules use CloudFormation hooks** — evaluate BEFORE resource
  creation, preventing non-compliant deployments.
- **Config API calls cost money.** Each `put-config-rule` and
  `start-config-rules-evaluation` is billable. Large fleets (100+ rules,
  frequent evaluations) can exceed $1,000/month. Conformance packs amplify.
- **Config rule scope narrows evaluation.** A scope of
  `resourceTypes: ["AWS::S3::Bucket"]` evaluates only S3 buckets. Without
  a scope, the rule evaluates ALL supported types — potentially exceeding
  timeouts and Lambda cost for custom rules.
- **Tag-based scope filters by tags.** `tagKey: "Environment",
  tagValue: "prod"` evaluates only resources tagged `Environment=prod`.
  Useful for phased compliance rollouts.
- **SSM Automation documents must be in the SAME region** as the Config
  rule. Cross-region remediation is not supported.
- **Deletion is eventual.** `delete-config-rule` marks for deletion; rule
  may take up to 6 hours to fully delete. During this window, the rule
  continues to evaluate. `ConfigRuleState` shows `DELETING`.

### Step 1: Pre-check gate — PREREQUISITES_MISSING if any check fails

Run ALL pre-checks. If ANY fails, verdict is PREREQUISITES_MISSING with
failed checks enumerated. Do NOT execute.

**For ALL operations:**
1. Recorder exists and `status.recording = true`.
2. Delivery channel exists with valid S3 bucket.
3. Rule name <= 128 chars, matches `^[a-zA-Z0-9-]+$`.
4. IAM principal holds `config:PutConfigRule` (and
   `config:PutConformancePack` or `config:PutOrganizationConfigRule`).
5. Total rule count + new <= 150 per region.

**For managed rule:** `ManagedRuleIdentifier` exists in managed rules list.
Required input parameters provided.

**For custom Lambda rule:** Lambda ARN exists. Function has resource-based
permission for `config.amazonaws.com`. IAM role has `config:PutEvaluations`.
Timeout <= 60s.

**For conformance pack:** Template body valid YAML/JSON, <= 256 KB. All
referenced managed rules have valid identifiers. Total packs + new <= 25.

**For organization config rule:** Account is management account or
delegated admin. Aggregator authorized. Metadata complete.

**For remediation:** SSM Automation document exists in-region. Config
service-linked role has `ssm:StartAutomationExecution`. `AutoRemediation`
is an explicit choice, not the default.

### Step 2: READY_TO_DEPLOY — emit deployment plan

If all pre-checks pass, emit `VERDICT: READY_TO_DEPLOY` with the exact CLI
sequence and CONFIRM gate. The plan includes: exact CLI command with all
flags populated, expected evaluation lag, expected compliance status, and
remediation behavior (automatic vs manual).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE** before any state-changing CLI.
- Snapshot current rule config before modification.
- Execute the CLI.
- Force immediate evaluation:
  `aws configservice start-config-rules-evaluation --config-rule-names <name>`.

### Step 4: Post-verification

1. `describe-config-rules` returns expected rule configuration.
2. `get-compliance-summary` shows Compliant/NonCompliant counts (1-30 min).
3. For custom rules: `describe-config-rule-evaluation-status` shows
   recent `LastSuccessfulInvocationTime`.
4. For remediation: `describe-remediation-executions-status` shows
   remediation executions.
5. For conformance packs: `describe-conformance-pack-compliance`.

## Common Config rule patterns (boilerplate)

### Managed rule — S3 public read prohibited

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Description": "Detects S3 buckets that allow public read access.",
    "Source": {"Owner": "AWS", "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"},
    "Scope": {"ComplianceResourceTypes": ["AWS::S3::Bucket"]},
    "ConfigRuleState": "ACTIVE"
  }'
```

### Managed rule with remediation (SSM Automation)

```bash
# 1. Create the rule
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Source": {"Owner": "AWS", "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"},
    "Scope": {"ComplianceResourceTypes": ["AWS::S3::Bucket"]}
  }'

# 2. Attach remediation (auto-remediate)
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "AWS-DisableS3BucketPublicReadWrite",
    "Automatic": true,
    "MaximumAutomaticAttempts": 3,
    "RetryAttemptSeconds": 600,
    "Parameters": {"S3BucketName": {"ResourceValue": {"Value": "RESOURCE_ID"}}}
  }]'
```

### Custom Lambda rule — tag enforcement

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "ec2-required-tags",
    "Description": "Ensures all EC2 instances have Environment, Owner, CostCenter tags.",
    "Source": {
      "Owner": "CUSTOM_LAMBDA",
      "SourceIdentifier": "arn:aws:lambda:us-east-1:111111111111:function:config-rule-required-tags",
      "SourceDetails": [{"EventSource": "aws.config", "MessageType": "ConfigurationItemChangeNotification"}]
    },
    "Scope": {"ComplianceResourceTypes": ["AWS::EC2::Instance"]},
    "InputParameters": "{\"requiredTags\": \"Environment,Owner,CostCenter\"}",
    "ConfigRuleState": "ACTIVE"
  }'

# Lambda permission for Config invocation (REQUIRED)
aws lambda add-permission \
  --function-name config-rule-required-tags \
  --statement-id AllowConfigToInvoke \
  --action lambda:InvokeFunction \
  --principal config.amazonaws.com \
  --source-account 111111111111
```

### Conformance pack — CIS AWS Foundations Benchmark

```bash
aws configservice put-conformance-pack \
  --conformance-pack-name "cis-aws-foundations-benchmark" \
  --template-body '
Resources:
  IamNoInlinePolicyRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: iam-no-inline-policy
      Source: {Owner: AWS, SourceIdentifier: IAM_NO_INLINE_POLICY_CHECK}
      Scope: {ComplianceResourceTypes: ["AWS::IAM::User"]}
  RootMfaEnabledRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: root-mfa-enabled
      Source: {Owner: AWS, SourceIdentifier: ROOT_ACCOUNT_MFA_ENABLED}
      MaximumExecutionFrequency: One_Hour
'
```

### Periodic rule — evaluate every 6 hours

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "iam-password-policy-check",
    "Description": "Checks the account password policy meets minimum requirements.",
    "Source": {"Owner": "AWS", "SourceIdentifier": "IAM_PASSWORD_POLICY"},
    "MaximumExecutionFrequency": "Six_Hours",
    "ConfigRuleState": "ACTIVE"
  }'
```

Account-level rules (not scoped to a resource type) MUST be periodic
because there is no resource change to trigger evaluation.

### Organization config rule — org-wide managed rule

```bash
aws configservice put-organization-config-rule \
  --organization-config-rule '{
    "OrganizationConfigRuleName": "org-s3-public-read-prohibited",
    "OrganizationManagedRuleMetadata": {
      "Description": "Org-wide: no S3 buckets with public read access.",
      "RuleIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
      "ResourceTypesScope": ["AWS::S3::Bucket"]
    },
    "ExcludedAccounts": []
  }'
```

Must be deployed from the management account or delegated admin. Member
accounts cannot modify or delete org rules.

Additional pattern (proactive rule via CloudFormation hooks) in
`references/config-rule-catalog.md`.

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

- NEVER start with conversational preamble — the VERDICT block is the
  FIRST line, always.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or
  `[FAIL]` and a specific reason for each failure.
- NEVER deploy a rule without verifying the configuration recorder is
  RUNNING. A rule on a stopped recorder reports stale compliance.
- NEVER emit a CLI command with placeholder flags in a READY_TO_DEPLOY
  plan — every field must be populated with actual values.
- NEVER omit the CONFIRM gate as the first STEPS entry.
- NEVER claim auto-remediation is active when `Automatic` is not explicitly
  `true`. The default is manual.
- NEVER deploy a custom Lambda rule without verifying the Lambda permission
  for `config.amazonaws.com` exists.

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
  - Evaluation mode: configuration-change triggered. Evaluates on S3 bucket
    creation/update/delete. MaximumExecutionFrequency controls periodic
    re-evaluation of unchanged resources (default 24h).
  - To force immediate evaluation:
    aws configservice start-config-rules-evaluation --config-rule-names s3-bucket-public-read-prohibited
  - Consider attaching remediation (AWS-DisableS3BucketPublicReadWrite).
```

## NEVER (top 5 — full list of 15 anti-patterns in references)

- NEVER deploy a Config rule without first verifying the configuration
  recorder is running. A stopped recorder means ALL rules report stale
  compliance — the rule appears active but evaluates nothing.
- NEVER assume `put-config-rule` triggers immediate evaluation. Always run
  `start-config-rules-evaluation` after creating a rule.
- NEVER assume remediation is automatic. Adding an SSM Automation document
  does NOT auto-remediate unless `Automatic: true` is explicitly set.
- NEVER deploy a custom Lambda rule without verifying the Lambda
  resource-based permission for `config.amazonaws.com`. Without it, Config
  silently fails to invoke the function.
- NEVER use periodic evaluation for security-critical rules when
  configuration-change evaluation is available. Periodic can take up to 24h;
  configuration-change evaluates within minutes.

## Expert heuristic: stale compliance vs real compliance

A Config rule showing "Compliant" means the rule's most recent evaluation
found resources compliant — which may be hours, days, or weeks ago if the
recorder is stopped or the rule hasn't evaluated recently.

**Diagnostic steps:**
1. `describe-configuration-recorder-status` — if `recording: false`, start it.
2. `describe-config-rule-evaluation-status` — check `LastSuccessfulInvocationTime`.
3. Force evaluation: `start-config-rules-evaluation --config-rule-names <name>`.
4. Wait 1-30 minutes, then re-check compliance.

Full diagnostic decision tree and per-rule-type staleness indicators in
`references/config-rule-catalog.md`.

ALWAYS pair Config rule deployment with a recorder status check. A
correctly configured rule on a stopped recorder is a false sense of
security.

## Pre-flight safety checks (run before any provisioning CLI)

- **MANDATORY CONFIRMATION GATE** before any state-changing operation.
- **PutConfigRule overwrites the entire rule.** Snapshot before modification:
  `aws configservice describe-config-rules --config-rule-names <name> --output json > /tmp/<name>-backup-$(date +%s).json`
- For custom Lambda rules: verify resource-based policy includes
  `config.amazonaws.com` permission. #1 cause of custom rule errors.
- For remediation: verify SSM document exists in-region AND Config
  service-linked role has `ssm:StartAutomationExecution`.
- For conformance packs: validate template YAML before deployment.
- Prefer configuration-change over periodic for security-critical checks.

## Recent AWS features (2024-2026)

- **Proactive Config rules (2024-2025):** evaluate CloudFormation templates
  BEFORE resource creation via CloudFormation hooks. Shifts from detective
  to preventive compliance.
- **Conformance pack templates from Git repositories (2024):** deploy from
  GitHub/CodeCommit without uploading template bodies. Enables
  version-controlled compliance-as-code.
- **Organization conformance packs (2024-2025):** deploy across an entire
  org from the management account with a single API call.
- **Config rule coverage for 300+ resource types (2025):** expanded support
  including AppRunner, Cedar policies, Bedrock guardrails.
- **Security Hub automated response (2025):** trigger SSM Automation
  directly from Config findings without custom Lambda. Reduces remediation
  latency from minutes to seconds.
- **Config data export to S3 with Parquet (2024):** configuration snapshots
  and compliance history in Parquet for Athena querying.
- **Resource aggregation across regions (2024-2025):** improved multi-region
  aggregation with lower latency.

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
