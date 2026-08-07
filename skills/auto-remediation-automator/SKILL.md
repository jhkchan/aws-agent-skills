---
name: auto-remediation-automator
description: >-
  Designs and implements automated remediation workflows linking AWS Config
  rules to SSM Automation runbooks. Detects non-compliant resources via
  managed or custom Config rules, maps each finding to the correct SSM
  document (AWS-DisableS3BucketPublicAccess, AWS-EnableS3BucketEncryption,
  AWS-IAMRevokeUnusedAccessKey, custom runbooks for security-group or
  tagging fixes), wires the remediation configuration
  (put-remediation-configurations) with automatic vs manual trigger
  semantics, and adds safety gates (snapshot, dry-run, CloudTrail audit,
  SSM Change Manager approval). Covers EventBridge-on-Config alternatives,
  conformance packs for bulk remediation, and Config timeline verification.
  Emits AUTOMATED with a workflow template or MANUAL_STEP_REQUIRED with the
  specific gap. Use when building auto-remediation for Config findings,
  wiring SSM Automation to Config rules, designing conformance-pack
  remediation, or hardening an existing remediation flow.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline workflow design. Live deployment
  uses aws configservice put-config-rule, put-remediation-configurations,
  describe-remediation-configurations, describe-remediation-execution-status,
  aws ssm create-document, describe-document, start-automation-execution,
  get-automation-execution, and aws cloudformation deploy (for conformance
  packs) — AWS CLI v2, SSO or key-based credentials.
keywords:
  - AWS Config
  - SSM Automation
  - auto-remediation
  - remediation configuration
  - put-remediation-configurations
  - conformance packs
  - AWS-DisableS3BucketPublicAccess
  - AWS-EnableS3BucketEncryption
  - AWS-IAMRevokeUnusedAccessKey
  - AWS-AttachIAMManagedPolicy
  - Config Rule
  - NON_COMPLIANT
  - EventBridge
  - SSM Change Manager
  - CloudTrail audit
  - Config timeline
  - governance automation
tags: [aws-config, ssm-automation, auto-remediation, governance, conformance-packs, eventbridge, automate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATED | MANUAL_STEP_REQUIRED"
  when_to_use: >-
    Designing auto-remediation for AWS Config findings, wiring SSM
    Automation runbooks to Config rules, deciding between automatic and
    manual remediation triggers, building conformance-pack bulk remediation,
    adding EventBridge-driven custom remediation, or hardening an existing
    remediation workflow with safety gates and audit.
  activation_triggers:
    - "automate Config remediation"
    - "wire SSM to Config rule"
    - "put-remediation-configurations"
    - "automatic remediation setup"
    - "conformance pack remediation"
    - "EventBridge Lambda remediation"
    - "SSM Automation runbook for Config"
    - "NON_COMPLIANT auto-fix"
    - "remediation safety gate"
    - "Config timeline verification"
  invocation_schema: >-
    Input: either (a) a Config rule definition (managed identifier or custom
    Lambda rule) plus target non-compliant resource examples, OR (b) a
    remediation requirement ("auto-disable public S3 buckets", "revoke
    exposed IAM keys on detection"). Output: deterministic REMEDIATION
    block per rule — WORKFLOW/TRIGGER/SAFETY/AUDIT/VERDICT — where VERDICT
    is AUTOMATED (workflow template ready) or MANUAL_STEP_REQUIRED (specific
    gap cited).
---

# Auto-Remediation Automator

## Mindset

**One-line takeaway:** every auto-remediation workflow is a four-stage
pipeline — **detect** (Config rule) → **decide** (remediation
configuration: automatic or manual) → **execute** (SSM Automation runbook)
→ **verify** (Config re-evaluates and timeline confirms COMPLIANT). A gap
in ANY stage produces a silent failure: the rule fires, but nothing is
fixed, or the fix is applied without safety checks, or the fix lands but
no one knows.

- **Detection** without **remediation configuration** is noise: the rule
  emits NON_COMPLIANT forever and operators develop alert fatigue.
- **Automatic trigger** is irreversible by default: the moment Config
  marks a resource NON_COMPLIANT, SSM fires the runbook. There is no
  human in the loop. This is the right choice for low-risk, reversible
  fixes (S3 public access, encryption enablement) and the wrong choice
  for destructive fixes (revoking an IAM policy that an application may
  depend on, deleting a security group rule that may be a false
  positive).
- **Verification is the closing gate.** A workflow that fires the runbook
  but never confirms COMPLIANT status is half-built. Config's re-election
  cadence and the SSM execution status together form the audit trail.

## Quick navigation

| You want to... | Go to |
|---|---|
| Pick a managed SSM runbook for a common finding | Step 3 + Appendix A |
| Decide automatic vs manual trigger | Step 4 (trigger matrix) |
| Wire `put-remediation-configurations` correctly | Step 5 + worked CLI |
| Build a custom SSM Automation document | Step 6 |
| Use EventBridge instead of native remediation | Step 7 |
| Roll out bulk remediation via conformance pack | Step 8 |
| Add safety gates (snapshot, approval, dry-run) | Step 9 |
| Audit and verify a remediation that already ran | Step 10 |
| Avoid common destructive-change pitfalls | Anti-Patterns |
| Recent features (Change Manager, conformance packs) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **`Automatic: true` fires on every NON_COMPLIANT evaluation.** There
   is no batching, no deduplication, no approval. If the rule re-evaluates
   hourly and the resource stays NON_COMPLIANT (e.g., a misconfigured CI
   pipeline keeps recreating it), SSM executes the runbook every hour.
   Always rate-limit via the rule's `MaximumExecutionFrequency` and
   consider a manual trigger for high-blast-radius fixes.
2. **SSM document parameters MUST map to Config resource identifiers.**
   The `ResourceValue` of type `RESOURCE_ID` is what Config injects. A
   remediation configuration whose static parameters do not match the
   SSM document's expected input silently fails execution.
3. **`put-remediation-configurations` is idempotent on
   `ConfigRuleName`.** Re-calling it overwrites the prior configuration
   atomically — no version history. Always capture the current state
   first (`describe-remediation-configurations`) before modifying.
4. **SSM Automation assumes a service role** (`AWS-SSM-AutomationExecutionRole`
   or a custom role). A missing or misconfigured role produces
   `ACCESS_DENIED` on execution — the remediation config looks healthy
   but no runbook ever runs successfully.
5. **Conformance-pack remediations are NOT implicit.** A conformance pack
   deploys rules; remediation configurations are a SEPARATE section in
   the pack YAML (`RemediationConfiguration`). Many operators ship a
   pack with rules only and assume remediation is wired.

## Pre-flight: data requirements

Designing a remediation workflow requires these inputs:

| Input | Source | Why |
|---|---|---|
| Config rule name + scope | `describe-config-rules` | The rule that emits NON_COMPLIANT |
| Resource type targeted by rule | `Source.Scope` (`AWS::S3::Bucket`, etc.) | Drives SSM runbook selection |
| Sample NON_COMPLIANT resource IDs | `get-compliance-details-by-config-rule` | Concrete parameters for the runbook |
| Available SSM documents | `ssm list-documents --document-type Automation` | Whether a managed runbook fits or a custom one is needed |
| Existing remediation configs | `describe-remediation-configurations` | Don't overwrite blindly |
| SSM service role ARN | `iam get-role` on `AWS-SSM-AutomationExecutionRole` | Execution identity |
| Conformance pack status (if applicable) | `describe-conformance-packs` | Pack deployment state |

**If the input is malformed** (missing Config rule name, ambiguous
resource type), emit:

```text
REMEDIATION: <reference>
RULE: <rule-name>
VERDICT: ERROR
REASON: Cannot design remediation — Config rule and target resource type are required inputs.
GAP: Re-supply describe-config-rules output for the rule and a sample of NON_COMPLIANT resource IDs.
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious Config + SSM behaviors

These behaviors change the workflow design if ignored:

- **`put-remediation-configurations` accepts a `TargetId` for org-level
  rules.** When the Config rule is deployed via an organization
  conformance pack, the remediation must be configured at the org
  level (`TargetType: AWS_ACCOUNT`) — member-account-level remediation
  configurations are ignored for org-deployed rules.

- **`Automatic: true` remediation does NOT fire on existing NON_COMPLIANT
  resources.** It only fires on NEW NON_COMPLIANT evaluations. To
  remediate the existing backlog, you must explicitly call
  `start-remediation-execution` per resource. This is the most common
  "I configured remediation and nothing happened" issue.

- **SSM Automation execution role is a service role, NOT the caller's
  role.** Config assumes a role to invoke SSM; SSM assumes a role to
  execute the runbook. Two service roles, both pre-provisioned. A
  single `AssumeRole` chain failure produces `ACCESS_DENIED` deep in
  the execution history.

- **The SSM document `Outputs` are NOT visible in the Config timeline.**
  Config records resource state changes (NON_COMPLIANT → COMPLIANT).
  SSM records runbook execution status (Success/Failed). To
  reconstruct what happened, you must join the two via timestamps in
  CloudTrail — there is no native join.

- **`AWS-Config-*` and `AWS-*` SSM documents are AWS-managed and
  versioned by AWS.** You cannot edit them. When AWS ships a new
  version, the remediation configuration automatically picks it up
  unless you pinned a specific version in `DocumentVersion`. Pinning
  is safer for stability; floating is better for bug fixes.

- **A Config rule scoped to a resource type that is NOT recorded by
  the recorder will never emit NON_COMPLIANT.** Remediation wired to
  such a rule is dead configuration. Always verify the recorder scope
  includes the rule's target resource type before wiring remediation.

- **`start-remediation-execution` is synchronous API but asynchronous
  execution.** The API returns immediately with an `ExecutionId`. The
  runbook continues executing for seconds to minutes. Poll
  `describe-remediation-execution-status` for completion.

- **SSM Automation step failures do NOT roll back.** Each step is
  independent. A multi-step runbook that fails on step 3 of 5 leaves
  steps 1-2 applied. Custom runbooks must include explicit rollback
  steps (`onFailure: abort` is the default, but earlier mutations
  persist).

- **EventBridge-driven remediation (Config state-change → Lambda) is
  not deduplicated.** Config emits a state-change event on every
  evaluation transition. A flapping resource (NON_COMPLIANT →
  COMPLIANT → NON_COMPLIANT) triggers the Lambda on every transition.
  Idempotency is the consumer's responsibility.

- **Conformance-pack `RemediationConfiguration` blocks use the SSM
  document name, not ARN.** A typo in the document name produces a
  silent deployment failure (the pack reports CREATE_COMPLETE but the
  remediation is not wired).

### Step 1: Classify the trigger source

For each Config rule that emits NON_COMPLIANT, classify the trigger:

| Trigger class | Config rule type | Example | Notes |
|---|---|---|---|
| AWS-managed, resource-scoped | `AWS::S3::Bucket`, `AWS::IAM::User`, etc. | `s3-bucket-public-read-prohibited` | Best fit for SSM-managed runbooks. Clear resource ID. |
| AWS-managed, periodic | `AWS::::Account` scope, `MaximumExecutionFrequency` | `iam-password-policy` | No specific resource — SSM remediation typically not applicable. Use a Lambda + EventBridge pattern. |
| Custom, Lambda-triggered | `Source.Owner: CUSTOM_LAMBDA` | Custom encryption check | Resource ID is in the evaluation payload. SSM remediation applicable. |
| Organization conformance pack | Deployed at org level | Pack-based security baseline | Remediation must be configured at org level too. |

If the rule is periodic with no resource ID, EventBridge → Lambda is
typically the only viable pattern. Mark this in the workflow design.

### Step 2: Map the resource type to a remediation strategy

| Resource type | Common finding | Managed runbook | Strategy |
|---|---|---|---|
| `AWS::S3::Bucket` | public read access | `AWS-DisableS3BucketPublicAccess` | Reversible — automatic OK |
| `AWS::S3::Bucket` | missing encryption | `AWS-EnableS3BucketEncryption` | Reversible — automatic OK |
| `AWS::S3::Bucket` | missing versioning | `AWS-EnableS3BucketVersioning` | Reversible — automatic OK |
| `AWS::IAM::User` | unused access key | `AWS-IAMRevokeUnusedAccessKey` | Reversible — automatic OK with caveat |
| `AWS::IAM::User` | excessive privileges | `AWS-AttachIAMManagedPolicy` (add) / custom (detach) | Detach is risky — manual trigger |
| `AWS::EC2::SecurityGroup` | open to 0.0.0.0/0 | No managed runbook — custom needed | Reversible but verify false positives — manual |
| `AWS::EC2::Instance` | missing required tags | Custom SSM doc (`AWS-ApplyIAMTags` + custom) | Reversible — automatic OK |
| `AWS::CloudTrail::Trail` | logging disabled | `AWS-EnableCloudTrailLogging` | Reversible — automatic OK |

**If no managed runbook exists** for the resource/finding combination, a
custom SSM Automation document is required (Step 6). The verdict tilts
toward MANUAL_STEP_REQUIRED until the custom document is built and
tested.

### Step 3: Pick the SSM Automation document

For each candidate, verify the document:

```bash
aws ssm describe-document \
  --name AWS-DisableS3BucketPublicAccess \
  --query 'Document.[Name,Version,Status]' --output json
```

If the document does not exist, the remediation configuration cannot
be created. A common pitfall is referencing a managed runbook that is
not available in the region (some AWS-managed runbooks are
region-specific).

Document parameter contract — for
`AWS-DisableS3BucketPublicAccess`:

| Parameter | Type | Source |
|---|---|---|
| `S3BucketName` | String | `ResourceValue: RESOURCE_ID` (Config injects the bucket name) |
| `AutomationAssumeRole` | String | Static: the SSM service role ARN |

A remediation configuration without the right `ResourceValue` mapping
fails at execution. Always cross-reference the document's parameter
list with the remediation configuration.

### Step 4: Decide automatic vs manual trigger (the trigger matrix)

| Rule characteristic | Trigger | Why |
|---|---|---|
| Reversible fix, low blast radius (S3 public access, encryption enablement) | **Automatic** | No human in the loop; risk of inaction > risk of action |
| Destructive fix (security group rule deletion, IAM policy detach) | **Manual** | False positive risk; require API call to execute |
| Multi-step workflow with side effects (terminate instance, revoke credential in use) | **Manual** | Application impact; route through SSM Change Manager |
| New workflow, no production validation | **Manual** until validated, then switch to Automatic | Avoid surprise execution on misclassified resources |
| High-volume finding (> 100 resources/day) | **Automatic with rate limit** (MaximumExecutionFrequency) | Manual backlog grows unmanageably |

**Decision rule:** default to **manual** unless ALL of the following
are true: (a) the fix is reversible within 5 minutes, (b) the runbook
has been tested in pre-prod on real NON_COMPLIANT resources, (c) a
CloudTrail alarm is configured for the SSM execution, (d) a rollback
path exists and is documented.

### Step 5: Wire the remediation configuration

CLI pattern for a single rule with automatic trigger:

```bash
aws configservice put-remediation-configurations \
  --remediation-configurations '[
    {
      "ConfigRuleName": "s3-bucket-public-read-prohibited",
      "TargetType": "SSM_DOCUMENT",
      "TargetId": "AWS-DisableS3BucketPublicAccess",
      "Automatic": true,
      "MaximumAutomaticAttempts": 3,
      "RetryAttemptSeconds": 600,
      "Parameters": {
        "S3BucketName": {"ResourceValue": {"Value": "RESOURCE_ID"}},
        "AutomationAssumeRole": {"StaticValue": {"Values": ["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}
      }
    }
  ]'
```

Common errors and fixes:

| Error | Cause | Fix |
|---|---|---|
| `AccessDeniedException` | SSM service role missing or wrong ARN | Create `AWS-SSM-AutomationExecutionRole` via `iam create-role` with the `AmazonSSMAutomationRole` policy |
| `ValidationException: SSM document not found` | Wrong `TargetId` or document not in region | Verify with `ssm describe-document --name <name>` |
| `InvalidParameterValue` for parameters | Static value where dynamic expected, or vice versa | Cross-reference document parameter list |
| Remediation configured but no executions | Rule exists but no NEW evaluations since config was set | Call `start-remediation-execution` for existing NON_COMPLIANT resources |

Verify the configuration landed:

```bash
aws configservice describe-remediation-configurations \
  --config-rule-names s3-bucket-public-read-prohibited --output json
```

### Step 6: Build a custom SSM Automation document (when no managed runbook fits)

Custom runbook template (YAML shorthand):

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Revoke ingress rule on a security group open to 0.0.0.0/0'
parameters:
  GroupId:
    type: String
    description: 'The security group ID (Config injects via RESOURCE_ID)'
  AutomationAssumeRole:
    type: String
    description: 'The SSM execution role ARN'
mainSteps:
  - name: GetOpenRules
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: DescribeSecurityGroupRules
      Filters:
        - Name: group-id
          Values: ['{{ GroupId }}']
        - Name: cidr
          Values: ['0.0.0.0/0']
    outputs:
      - Name: RuleIds
        Selector: '$.SecurityGroupRules[].SecurityGroupRuleId'
        Type: StringList
  - name: VerifyFinding
    action: aws:branch
    inputs:
      Choices:
        - NextStep: RevokeRules
          Variable: '{{ GetOpenRules.RuleIds }}'
          Operation: NotEquals
          Value: '[]'
      Default: CompleteNoOp
  - name: RevokeRules
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: RevokeSecurityGroupIngress
      GroupId: '{{ GroupId }}'
      IpPermissions: '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]'
    isCritical: true
    onFailure: abort
  - name: CompleteNoOp
    action: aws:sleep
    inputs:
      Duration: PT0S
```

Create the document:

```bash
aws ssm create-document \
  --name Custom-RevokeOpenSecurityGroupIngress \
  --document-type Automation \
  --document-format YAML \
  --content file://custom-runbook.yaml \
  --target-type '/AWS::EC2::SecurityGroup'
```

Test before wiring remediation:

```bash
aws ssm start-automation-execution \
  --document-name Custom-RevokeOpenSecurityGroupIngress \
  --parameters '{"GroupId":["sg-0abc123"],"AutomationAssumeRole":["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}'

aws ssm get-automation-execution \
  --automation-execution-id <execution-id> \
  --query 'AutomationExecution.AutomationExecutionStatus'
```

A custom runbook without a tested execution is the most common cause
of a "remediation wired but doesn't actually fix" failure.

### Step 7: EventBridge alternative (Config state-change → Lambda)

Use when: the remediation requires custom logic that an SSM document
cannot express (call a third-party API, perform multi-resource
orchestration, query a CMDB first).

EventBridge rule pattern:

```bash
aws events put-rule \
  --name config-remediation-custom \
  --event-pattern '{
    "source": ["aws.config"],
    "detail-type": ["Config Configuration Item Change"],
    "detail": {
      "configurationItem": {
        "configurationItemStatus": ["OK"],
        "resourceType": ["AWS::S3::Bucket"],
        "complianceType": ["NON_COMPLIANT"]
      }
    }
  }'
```

Or simpler, on compliance change:

```bash
aws events put-rule \
  --name config-compliance-change \
  --event-pattern '{
    "source": ["aws.config"],
    "detail-type": ["Config Rules Compliance Changed"],
    "detail": {"newEvaluationResult": {"complianceType": ["NON_COMPLIANT"]}}
  }'
```

Add the Lambda target with DLQ:

```bash
aws events put-targets \
  --rule config-compliance-change \
  --targets '[{"Id":"custom-remediation-lambda","Arn":"arn:aws:lambda:us-east-1:111111111111:function:custom-remediation","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:config-remediation-dlq"}}]'
```

Trade-off table:

| Dimension | Native SSM remediation | EventBridge + Lambda |
|---|---|---|
| Setup complexity | Low (one CLI call) | Medium (rule + Lambda + DLQ) |
| Custom logic | Limited to SSM steps | Full Lambda power |
| Built-in retry | `MaximumAutomaticAttempts` | Configure manually (Lambda async config) |
| Audit | SSM execution history | CloudTrail + Lambda logs |
| Idempotency handling | SSM is per-execution | Consumer's responsibility |

### Step 8: Conformance-pack bulk remediation

For multi-rule baselines, ship remediations inside the conformance pack
YAML. Sample:

```yaml
Resources:
  S3PublicReadProhibitedRule:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: s3-bucket-public-read-prohibited
      Source:
        Owner: AWS
        SourceIdentifier: AWS::S3::Bucket
      Scope:
        ComplianceResourceTypes:
          - AWS::S3::Bucket

  S3PublicReadRemediation:
    Type: AWS::Config::RemediationConfiguration
    Properties:
      ConfigRuleName: !Ref S3PublicReadProhibitedRule
      TargetType: SSM_DOCUMENT
      TargetId: AWS-DisableS3BucketPublicAccess
      Automatic: true
      Parameters:
        S3BucketName:
          ResourceValue:
            Value: RESOURCE_ID
        AutomationAssumeRole:
          StaticValue:
            Values:
              - !Sub 'arn:aws:iam::${AWS::AccountId}:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole'
```

Deploy:

```bash
aws configservice put-conformance-pack \
  --conformance-pack-name s3-security-baseline \
  --template-body file://conformance-pack.yaml \
  --region us-east-1
```

Verify both rule AND remediation landed:

```bash
aws configservice describe-remediation-configurations \
  --config-rule-names s3-bucket-public-read-prohibited
```

A pack in `CREATE_COMPLETE` does NOT guarantee remediation is wired —
verify explicitly.

### Step 9: Safety gates

Every remediation workflow MUST include at least one safety gate from
the table below. A workflow without any safety gate is unsafe by
construction.

| Gate | How | When to use |
|---|---|---|
| Pre-execution snapshot | SSM `aws:createImage` step before mutation | EC2 mutations, volume detach |
| Dry-run first | `aws:executeAwsApi` with `DryRun: true` | Security group, IAM changes |
| Approval gate | `aws:approve` step with SNS approvers | Destructive or production-impact remediation |
| SSM Change Manager | Route through Change Template + approval workflow | Production environments, regulated workloads |
| Maximum automatic attempts | `MaximumAutomaticAttempts: 3` and `RetryAttemptSeconds: 600` | Prevent infinite retry loops |
| CloudTrail alarm | Metric filter on `ssm:StartAutomationExecution` by specific doc | All workflows — non-negotiable |
| Config timeline verification | `get-resource-config-history` after execution | Confirm NON_COMPLIANT → COMPLIANT transition |
| Rollback runbook | Custom document with inverse operation | Every destructive remediation |

For automatic-trigger destructive remediations (security group
revoke, IAM policy detach), the workflow MUST route through SSM
Change Manager. A destructive automatic remediation without an
approval gate is the most common cause of "auto-remediation broke
my app" incidents.

### Step 10: Audit and verify

After a remediation executes, verify end-to-end:

```bash
# 1. SSM execution status
aws configservice describe-remediation-execution-status \
  --config-rule-name s3-bucket-public-read-prohibited \
  --resource-type AWS::S3::Bucket \
  --resource-id my-public-bucket

# 2. Config compliance state after remediation
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name s3-bucket-public-read-prohibited \
  --compliance-types COMPLIANT

# 3. CloudTrail audit trail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=StartAutomationExecution \
  --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S)

# 4. Config timeline for the resource
aws configservice get-resource-config-history \
  --resource-type AWS::S3::Bucket \
  --resource-id my-public-bucket \
  --limit 5
```

A remediation that reports Success in SSM but leaves the resource
NON_COMPLIANT in Config indicates the runbook executed but did not
fix the actual misconfiguration — typically a parameter mapping
error or a partial fix (e.g., disabled public access at the
bucket-policy level but not at the account level).

## Output format

```text
REMEDIATION: <reference>
RULE: <rule-name>
RESOURCE_TYPE: <AWS::...>
WORKFLOW:
  - Detection: <Config rule + scope>
  - Runbook: <SSM document name + version>
  - Trigger: AUTOMATIC | MANUAL
  - Safety gates: <list>
  - Audit: <CloudTrail + Config timeline>
TRIGGER: AUTOMATIC | MANUAL
SAFETY: <gates applied, or "NONE — destructive without gate" flag>
AUDIT: <CloudTrail + Config verification steps>
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
GAP: <if MANUAL_STEP_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or YAML for the remediation configuration>
```

### Worked example — AUTOMATED, simple S3 public access remediation

```text
REMEDIATION: prod-remediation-baseline
RULE: s3-bucket-public-read-prohibited
RESOURCE_TYPE: AWS::S3::Bucket
WORKFLOW:
  - Detection: AWS-managed Config rule s3-bucket-public-read-prohibited, scoped to AWS::S3::Bucket.
  - Runbook: AWS-DisableS3BucketPublicAccess (AWS-managed, floating version).
  - Trigger: AUTOMATIC (reversible fix; tested in pre-prod; CloudTrail alarm configured).
  - Safety gates: MaximumAutomaticAttempts=3, RetryAttemptSeconds=600, Config timeline verification.
  - Audit: CloudTrail metric filter on ssm:StartAutomationExecution for AWS-DisableS3BucketPublicAccess.
TRIGGER: AUTOMATIC
SAFETY: retry-limit, cloudtrail-alarm, config-verification
AUDIT:
  - aws configservice describe-remediation-execution-status --config-rule-name s3-bucket-public-read-prohibited
  - aws configservice get-resource-config-history --resource-type AWS::S3::Bucket --resource-id <bucket>
VERDICT: AUTOMATED
GAP: None
TEMPLATE:
  aws configservice put-remediation-configurations --remediation-configurations '[{"ConfigRuleName":"s3-bucket-public-read-prohibited","TargetType":"SSM_DOCUMENT","TargetId":"AWS-DisableS3BucketPublicAccess","Automatic":true,"MaximumAutomaticAttempts":3,"RetryAttemptSeconds":600,"Parameters":{"S3BucketName":{"ResourceValue":{"Value":"RESOURCE_ID"}},"AutomationAssumeRole":{"StaticValue":{"Values":["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}}}]'
```

### Worked example — MANUAL_STEP_REQUIRED, custom runbook missing

```text
REMEDIATION: sg-open-ingress-remediation
RULE: custom-sg-no-open-ingress
RESOURCE_TYPE: AWS::EC2::SecurityGroup
WORKFLOW:
  - Detection: Custom Lambda Config rule on AWS::EC2::SecurityGroup.
  - Runbook: NONE — no AWS-managed runbook exists for security-group ingress revocation.
  - Trigger: TBD (manual recommended; the fix is reversible but false-positive prone).
  - Safety gates: TBD.
  - Audit: TBD.
TRIGGER: MANUAL
SAFETY: NONE — workflow not yet built
AUDIT: NOT WIRED
VERDICT: MANUAL_STEP_REQUIRED
GAP: No managed SSM runbook for security-group revocation. Build and test Custom-RevokeOpenSecurityGroupIngress (template provided in Step 6) before wiring remediation. Verify the SSM execution role exists.
TEMPLATE: (custom SSM document — see Step 6)
```

## Anti-Patterns — NEVER do these things

- NEVER wire `Automatic: true` to an untested SSM runbook. The first
  production NON_COMPLIANT resource triggers immediate execution; if
  the runbook has a parameter mismatch or a destructive bug, the
  damage is done before any operator sees it. Always test in pre-prod
  with `start-automation-execution` on a sample resource first.

- NEVER assume `put-remediation-configurations` succeeds silently. It
  returns no error on success but does not validate that the SSM
  document parameters match. The first execution failure is your
  indication the contract is wrong. Always verify with
  `describe-remediation-configurations` and a single
  `start-remediation-execution` test.

- NEVER configure destructive remediations (IAM policy detach,
  security-group revoke, instance termination) with `Automatic: true`
  without an approval gate. A false-positive finding on a production
  resource causes an immediate outage. Use SSM Change Manager or
  `aws:approve` for any remediation that affects application traffic.

- NEVER forget to remediate the existing NON_COMPLIANT backlog.
  `Automatic: true` fires only on NEW evaluations. Resources that
  were already NON_COMPLIANT before the configuration was set remain
  so until you explicitly call `start-remediation-execution`.

- NEVER omit `MaximumAutomaticAttempts` and `RetryAttemptSeconds`.
  Defaults are 1 attempt with no retry window — a transient SSM
  failure produces a permanently unremediated resource. For automatic
  workflows, set `MaximumAutomaticAttempts: 3` and
  `RetryAttemptSeconds: 600` (10 minutes) at minimum.

- NEVER assume a conformance pack in `CREATE_COMPLETE` includes
  remediation. The default behavior is rules-only. Remediation must
  be an explicit `AWS::Config::RemediationConfiguration` resource in
  the pack YAML. Always verify with
  `describe-remediation-configurations` after deployment.

- NEVER use `ResourceValue: RESOURCE_ID` when the Config rule is
  periodic (no resource ID). Periodic rules emit NON_COMPLIANT at
  the account level; there is no resource ID to inject. Use static
  parameters or switch to EventBridge + Lambda with custom logic.

- NEVER wire remediation to a Config rule whose target resource type
  is NOT in the recorder's recording group. The rule will never
  emit NON_COMPLIANT (no configuration items exist to evaluate), so
  the remediation is dead configuration that lulls operators into a
  false sense of security.

- NEVER pin a managed-runbook version (`DocumentVersion: "1"`) without
  tracking AWS bug-fix releases. Pinning guarantees stability but
  blocks security patches. Set a calendar reminder to review the
  latest version quarterly and update.

- NEVER omit the CloudTrail alarm on `ssm:StartAutomationExecution`
  for the specific runbook. A misconfigured or compromised
  Config rule can fire remediations invisibly. The alarm is the
  operational visibility layer.

- NEVER assume SSM Automation step failures roll back. They do not.
  A multi-step runbook that fails on step 3 of 5 leaves steps 1-2
  applied. Custom runbooks MUST include explicit rollback steps for
  any mutating action.

- NEVER wire a remediation without verifying the SSM service role
  exists in the target account. `AWS-SSM-AutomationExecutionRole` is
  not auto-created; it must be provisioned via `iam create-role`
  with the `AmazonSSMAutomationRole` managed policy attached.
  Missing role → `ACCESS_DENIED` on every execution.

- NEVER use EventBridge + Lambda remediation without a DLQ. Config
  emits compliance-change events that may be dropped on Lambda
  failures. A missing DLQ produces silent data loss — the
  NON_COMPLIANT finding is never remediated and no one knows.

- NEVER recommend `Automatic: true` for any IAM-policy-detach
  remediation without a CMDB or application-dependency check.
  Detaching a policy an application depends on is an immediate
  outage. Always route through manual trigger or Change Manager.

- NEVER confuse `describe-remediation-execution-status` with Config
  compliance state. SSM "Success" means the runbook ran; Config
  "COMPLIANT" means the resource is actually fixed. Always verify
  both. A successful runbook that leaves the resource NON_COMPLIANT
  indicates a partial fix or a parameter mismatch.

- NEVER forget that organization conformance-pack remediations are
  configured at the ORG level. Member-account-level
  `put-remediation-configurations` calls are silently ignored for
  org-deployed rules. Always check whether the rule originated from
  an org pack before configuring remediation.

## Pre-flight safety checks (run before applying any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-remediation-configurations`, `start-remediation-execution`,
  `delete-remediation-configuration`, custom SSM `create-document`),
  emit:
  `CONFIRM: About to <action> for rule <rule> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`

- **Back up the current remediation configuration** before modifying:
  `aws configservice describe-remediation-configurations --config-rule-names <rule> > /tmp/<rule>-remediation-backup-$(date +%s).json`
  Remediation configurations have no version history.

- **Before switching from MANUAL to AUTOMATIC trigger**, run the
  runbook manually against at least 3 sample NON_COMPLIANT resources
  and verify all executions succeed AND flip the resource to
  COMPLIANT in Config.

- **Before deploying a conformance pack with remediation**, dry-run
  the CloudFormation template locally:
  `aws cloudformation validate-template --template-body file://conformance-pack.yaml`

- **For destructive remediations** (security-group revoke, IAM detach,
  instance termination), route through SSM Change Manager:
  create a Change Template, submit a change request, obtain approval,
  then execute. A direct automatic remediation without approval is
  an unsafe destructive action.

## Appendix A — Common managed SSM Automation runbooks

| Runbook | Purpose | Reversible |
|---|---|---|
| `AWS-DisableS3BucketPublicAccess` | Block public access on S3 bucket | Yes |
| `AWS-EnableS3BucketEncryption` | Apply SSE-KMS or SSE-S3 | Yes |
| `AWS-EnableS3BucketVersioning` | Enable S3 versioning | Yes |
| `AWS-IAMRevokeUnusedAccessKey` | Deactivate unused IAM access key | Yes (reactivate) |
| `AWS-AttachIAMManagedPolicy` | Attach a managed policy | Yes (detach) |
| `AWS-EnableCloudTrailLogging` | Resume CloudTrail logging | Yes |
| `AWS-EnableConfigRule` | Re-enable a Config rule | Yes |
| `AWS-RestartEC2Instance` | Restart stopped EC2 | Yes |
| `AWS-UpdateLinuxAmi` | Patch and update Linux AMI | Partial — pin to known-good AMI for rollback |
| `AWS-AttachEBSVolume` | Attach EBS | Yes (detach) |

## Appendix B — Decision tree (which workflow pattern)

```
Is there a managed SSM runbook for the resource/finding?
├─ Yes → Is the fix reversible within 5 minutes?
│       ├─ Yes → Tested in pre-prod? ── Yes → AUTOMATIC (Step 5)
│       │                                   └── No → MANUAL until validated
│       └─ No  → MANUAL with Change Manager (Step 9)
└─ No  → Build custom SSM doc (Step 6) OR EventBridge+Lambda (Step 7)
        Choose SSM doc if logic fits SSM steps.
        Choose Lambda if multi-resource orchestration or external API call required.
        Either way: MANUAL_STEP_REQUIRED until built + tested.
```

## Recent AWS features (2024-2026)

- **SSM Change Manager GA (2024):** Native change-approval workflow
  for SSM Automation runbooks. Required for production destructive
  remediations. Wire the remediation runbook as a Change Template
  and route through the approval workflow instead of direct
  `Automatic: true`.
- **Config conformance pack remediation enhancements:** Bulk remediation
  configurations inside the pack YAML are now first-class. Previously
  required separate `put-remediation-configurations` calls per rule.
- **Config evaluation mode (2024):** Hybrid evaluation for periodic
  rules — combines periodic with configuration-change trigger.
  Useful for IAM rules that previously could not drive resource-
  scoped remediation.
- **EventBridge global endpoints for remediation pipelines (2024-2025):**
  Multi-region failover for event-driven remediation. Useful for
  global security-baseline remediations that must continue operating
  during a regional event.
- **SSM Automation runbook versioning (2024):** Default version
  selection per document. Pin the default version explicitly to
  avoid surprise upgrades when AWS ships a new managed-runbook
  version.

## Domain

AWS CloudOps / Governance Automation — Config-driven remediation.

## AWS documentation

- **AWS Config Remediation** — https://docs.aws.amazon.com/config/latest/developerguide/remediation-setup.html
- **SSM Automation Runbooks** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssa-docs.html
- **SSM Change Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-change-manager.html
- **AWS Config Conformance Packs** — https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html
- **EventBridge Config Events** — https://docs.aws.amazon.com/config/latest/developerguide/example-config.html
