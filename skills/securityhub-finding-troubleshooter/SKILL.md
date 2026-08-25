---
name: securityhub-finding-troubleshooter
description: Diagnoses and resolves AWS Security Hub findings through a standard-driven decision tree covering CIS AWS Foundations Benchmark, PCI DSS 3.2.1, AWS Foundational Security Best Practices (FSBP), and NIST 800-53. Walks each finding through its lifecycle (New, Notified, Suppressed, Resolved) and severity (Critical, High, Medium, Low) to the failed control, then to the per-service remediation (S3 BPA, IAM password policy, EC2 IMDSv2, KMS rotation, CloudTrail data events, Config conformance). Identifies findings stuck in Resolved-but-still-failing, NOT_AVAILABLE with StatusReasons, multi-account aggregation gaps, and standards disabled mid-audit. Configures custom actions (EventBridge rule to Lambda) for auto-remediation, manages enabled-standards, and applies Automation Rules and custom controls. Emits ROOT_CAUSE_FOUND with the specific control failure, NEED_MORE_INFO, or ESCALATE. Use when triaging a Security Hub finding, diagnosing a control that will not resolve, or designing a remediation runbook.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline triage works from pasted ASFF finding JSON. Live-account diagnosis uses aws securityhub get-findings, get-findings-statistics, describe-standards, describe-hub, list-enabled-products, get-insights, update-findings, get-finding-aggregator, get-administrator-account, aws configservice describe-config-rules / describe-configuration-recorders, aws s3api get-public-access-block, aws iam...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing a Security Hub finding (single ASFF JSON, finding ID, or a list of findings from get-findings) for the failed control, walking the standard (CIS, PCI DSS, FSBP, NIST) to the per-service remediation (S3, IAM, EC2, KMS, CloudTrail, Config), diagnosing a finding stuck in Resolved-but-still-failing or NOT_AVAILABLE with StatusReasons, configuring custom actions (EventBridge rule to Lambda), managing enabled-standards mid-audit, applying Automation Rules or custom controls, or resolving multi-account aggregation gaps. Diagnoses runtime control failures — not posture reporting.
  when_not_to_use: Posture reporting and aggregate compliance scoring (use securityhub-control-compliance-auditor for FAILED/WARNING/PASSED control scoring across the account, or the auditor family for per-service config posture). Non-Security-Hub detections (GuardDuty, Inspector, Macie, Detective) use their own skills. Forensic chain of custody belongs to incident-response-automator.
  activation_triggers: Security Hub finding, Security Hub alert, troubleshoot Security Hub, Security Hub control failing, CIS control, PCI DSS control, FSBP control, Foundational Security Best Practices, NIST 800-53 control, Security Hub NOT_AVAILABLE, Security Hub StatusReason, finding stuck Resolved, Security Hub custom action, Security Hub Automation Rules, Security Hub custom control, Security Hub finding aggregator, enabled standards Security Hub, ASFF finding
  invocation_schema: 'Input: either (a) a Security Hub finding JSON (ASFF) or finding ID + product ARN for live lookup, optionally paired with the related Config rule evaluation; OR (b) a control ID (e.g., S3.1, CIS.1.3, PCI.S3.1) and resource ARN for live-account diagnosis. Output: a deterministic FINDING/VERDICT/REASON/LAYER/ EVIDENCE/SUPPRESSION/REMEDIATION block where VERDICT in {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and LAYER in {S3_BPA, IAM_PASSWORD_POLICY, IAM_MFA, EC2_IMDSV2, EC2_SG, KMS_ROTATION, CLOUDTRAIL_DATA_EVENTS, CONFIG_RECORDER, CUSTOM_ACTION_GAPPED, STANDARD_DISABLED, AGGREGATOR_GAP, AUTOMATION_RULE_MISCONFIGURED, FALSE_POSITIVE, AWS_SIDE, UNKNOWN}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Security Hub, ASFF, finding, control, CIS, PCI DSS, FSBP, NIST 800-53, compliance, remediation, custom action, EventBridge, Lambda, finding aggregator, Automation Rules, custom controls, enabled standards, suppression, troubleshooting
  tags: securityhub, security, compliance, cis, pci-dss, fsbp, nist, remediation, troubleshooting, eventbridge
---

# Security Hub Finding Troubleshooter

## What this skill does

Walks an AWS Security Hub finding (ASFF) from raw JSON to a confirmed
failed control with a per-service remediation. The diagnostic tree is
**standard-driven** (CIS, PCI DSS, FSBP, NIST 800-53). Each branch
identifies the failing resource, the per-service probe that confirms the
failure, and the specific remediation. The skill distinguishes true
control failures from findings stuck in Resolved-but-still-failing
race, NOT_AVAILABLE with StatusReasons, and aggregator gaps.

## Mindset

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset).
> A finding is a control-evaluation result, not a threat; read Compliance.Status and StatusReasons before probing the resource.

## STRICT output contract

Every investigation MUST emit exactly one diagnostic block per finding:

```text
FINDING: <finding-id or control-id:resource>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the control layer and the corroborating probe>
LAYER: <S3_BPA | IAM_PASSWORD_POLICY | IAM_MFA | EC2_IMDSV2 | EC2_SG |
        KMS_ROTATION | CLOUDTRAIL_DATA_EVENTS | CONFIG_RECORDER |
        CUSTOM_ACTION_GAPPED | STANDARD_DISABLED | AGGREGATOR_GAP |
        AUTOMATION_RULE_MISCONFIGURED | FALSE_POSITIVE | AWS_SIDE | UNKNOWN>
SEVERITY: <CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL>
STANDARD: <CIS | PCI_DSS | FSBP | NIST_800_53 | CUSTOM>
EVIDENCE:
  - <Security Hub finding summary — control ID, resource, severity, compliance status>
  - <corroborating probe — service CLI (s3api / iam / ec2 / kms / cloudtrail) output>
  - <false-positive ruled out — name the FP class tested and why it does not apply>
SUPPRESSION:
  - <if FALSE_POSITIVE: Automation Rules JSON to lower severity or archive>
  - <otherwise: "Not applicable — true control failure">
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification — usually aws securityhub get-findings re-check>
CONFIRM: Before any state-changing CLI, emit and await operator approval:
  "CONFIRM: About to <action> on <resource>. Proceed? (yes/no)"
```

A block without EVIDENCE containing at least one Security Hub field AND
one corroborating service probe is a contract violation. ROOT_CAUSE_FOUND
on a true failure requires positive control-failure evidence; on a
FALSE_POSITIVE layer, it requires benign-context evidence.

## Quick navigation

| If the finding control is... | Go to | First corroborating probe |
|---|---|---|
| S3 public access (S3.1 / S3.2 / S3.3 / PCI.S3.1-5) | Step 2a | `aws s3api get-public-access-block` |
| S3 bucket encryption (S3.4 / S3.6) | Step 2b | `aws s3api get-bucket-encryption` |
| S3 versioning (S3.9 / S3.10) | Step 2c | `aws s3api get-bucket-versioning` |
| IAM password policy (CIS.1.5-1.11 / PCI.IAM.1) | Step 3a | `aws iam get-account-password-policy` |
| IAM MFA on root / IAM users (CIS.1.4 / FSBP.IAM.7) | Step 3b | `aws iam get-account-summary` `AccountMFAEnabled` |
| IAM access keys older than 90 days (CIS.1.3 / FSBP.IAM.6) | Step 3c | `aws iam get-credential-report` |
| EC2 IMDSv2 required (EC2.8 / FSBP.EC2.8) | Step 4a | `aws ec2 describe-instances` `MetadataOptions` |
| EC2 security group open to 0.0.0.0/0 (EC2.2 / EC2.4 / PCI.EC2.2-4) | Step 4b | `aws ec2 describe-security-groups` |
| KMS rotation (KMS.3 / PCI.KMS.1) | Step 5 | `aws kms describe-keys` `EnableKeyRotation` |
| CloudTrail data events (CloudTrail.4 / CIS.2.7) | Step 6 | `aws cloudtrail describe-trails` + `get-event-selectors` |
| Config recorder enabled (Config.1) | Step 7 | `aws configservice describe-configuration-recorders` |
| `Compliance.Status = NOT_AVAILABLE` with StatusReasons | Step 8 | Read StatusReasons code, rule evaluation state |
| `Workflow.Status = RESOLVED` but still appearing | Step 9 | `aws configservice get-resource-config-history` |
| Aggregator / administrator account mismatch | Step 10 | `aws securityhub get-finding-aggregator` |
| Custom action wired but not firing | Step 11 | `aws events describe-rule` + Lambda permissions |
| Automation Rules not applying | Step 12 | `aws securityhub list-automation-rules` |
| Need control catalogue, suppression patterns | Reference | `references/control-catalogue-and-remediation.md` |

## Pre-flight: gather finding metadata

Before running any control-specific probe, gather the canonical Security
Hub metadata. A misread control ID (e.g., confusing `S3.1` public
access with `S3.4` encryption) routes the investigation to the wrong
layer.

### Account-wide pre-flight commands

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#account-wide-pre-flight-commands).
> Hub/standards/aggregator/administrator discovery, get-findings by ID, finding statistics, and Config rule probes.

### Finding-shape short-circuit

| Field | Value | Effect on investigation |
|---|---|---|
| `Compliance.Status` | `PASSED` | The control currently evaluates clean. A PASSED finding still in the console is stale — wait for the next eval cycle (5-12 min for change-triggered, 24h for periodic). |
| `Compliance.Status` | `FAILED` | True control failure — corroborate with the service probe. |
| `Compliance.Status` | `WARNING` | Resource is at risk but not strictly non-compliant. Treat as MEDIUM regardless of `Severity`. |
| `Compliance.Status` | `NOT_AVAILABLE` | The Config rule backing the control errored or has no resources in scope — read `Compliance.StatusReasons`. |
| `Workflow.Status` | `NEW` / `NOTIFIED` / `RESOLVED` / `SUPPRESSED` | Lifecycle. RESOLVED findings auto-archive after 3-5 days if the resource is fixed. |
| `RecordState` | `ACTIVE` / `ARCHIVED` | ARCHIVED findings are out of scope. |
| `Severity.Label` | `INFORMATIONAL` / `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` | Drives SLA, not the verdict. |
| `Product.Fields.StandardsArn` / `GeneratorId` | CIS / PCI / FSBP / NIST ARN | Identifies the standard and the control family. |
| `Resources[0].Type` | `AwsS3Bucket` / `AwsIamRole` / `AwsEc2Instance` / `AwsKmsKey` / `AwsCloudTrailTrail` | Determines which service probe applies. |

### Missing-context NEED_MORE_INFO

If the input is missing the finding JSON, finding ID, or sufficient
resource context, emit a NEED_MORE_INFO block listing the specific
missing fields (finding ID, account ID, region) and the next probe.

## Process — standard-driven decision tree

Pick the entry point based on the failing standard family, then walk
the service-specific probes in order. Each branch ends with either a
positive root-cause confirmation (the failing resource, confirmed by a
service probe) or a pass that moves to the next plausible layer. **Never
emit ROOT_CAUSE_FOUND without corroborating evidence from the service
CLI or Config.**

### Step 0: Non-obvious behaviours that change the diagnosis

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-0-non-obvious-behaviours-that-change-the-diagnosis).
> Seven diagnosis-changing behaviours: RESOLVED re-eval race, NOT_AVAILABLE semantics, severity mapping, aggregation latency, custom-control wiring, control-ID versioning, standard-disable staleness.

### Step 1: Symptom entry — pick the diagnostic branch

Map the failing control family to a branch. If the control ID is
ambiguous, first fetch the finding JSON and inspect `GeneratorId` and
`Resources[0].Type`.

| Standard / control family | Meaning | Branch |
|---|---|---|
| S3 public access / encryption / versioning | Bucket policy, BPA, SSE, MFA delete | Step 2 |
| IAM password / MFA / access keys | Identity controls | Step 3 |
| EC2 IMDSv2 / security groups | Compute hardening | Step 4 |
| KMS key rotation | Encryption-at-rest rotation | Step 5 |
| CloudTrail data events / multi-region | Audit log coverage | Step 6 |
| Config recorder coverage | Configuration baselining | Step 7 |
| `NOT_AVAILABLE` StatusReasons | Rule evaluation failure | Step 8 |
| Stuck `RESOLVED`-but-still-appearing | Re-eval race or stale cache | Step 9 |
| Cross-account aggregator gap | Aggregator misconfiguration | Step 10 |
| Custom action wired but not firing | EventBridge / Lambda permission gap | Step 11 |
| Automation Rules not applying | Rule criteria or scope misconfig | Step 12 |

### Step 2: S3 controls

#### 2a: Public access block (S3.1 / PCI.S3.1-5)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-2a--public-access-block-s31--pcis31-5).
> Account+bucket BPA and bucket policy/ACL cross-check probes.

**Verdict signals:**
- `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, and
  `RestrictPublicBuckets` all `true` at the account level → the
  account-level BPA is correct; the finding is from a per-bucket
  override or a stale eval. **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE`
  if the bucket has no public ACL/policy.
- Any account-level BPA flag `false` → **ROOT_CAUSE_FOUND**,
  `LAYER: S3_BPA`. Remediation: `aws s3control put-public-access-block`.

#### 2b: Bucket encryption (S3.4 / S3.6)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-2b--bucket-encryption-s34--s36).
> get-bucket-encryption probe.

**Verdict signals:**
- `ServerSideEncryptionConfiguration` is empty or absent →
  **ROOT_CAUSE_FOUND**, `LAYER: S3_BPA`. Remediation:
  `aws s3api put-bucket-encryption` with AES256 or aws:kms.

#### 2c: Versioning / MFA delete (S3.9 / S3.10)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-2c--versioning--mfa-delete-s39--s310).
> get-bucket-versioning probe.

**Verdict signals:**
- `Status` absent or `Suspended` → **ROOT_CAUSE_FOUND**,
  `LAYER: S3_BPA`. Remediation: `aws s3api put-bucket-versioning
  --versioning-configuration Status=Enabled`.

### Step 3: IAM controls

#### 3a: Password policy (CIS.1.5-1.11 / PCI.IAM.1)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-3a--password-policy-cis15-111--pciiam1).
> get-account-password-policy probe.

**Verdict signals:**
- `MinimumPasswordLength < 14`, `RequireSymbols=false`, etc. →
  **ROOT_CAUSE_FOUND**, `LAYER: IAM_PASSWORD_POLICY`. Remediation:
  `aws iam update-account-password-policy`.

#### 3b: MFA on root / IAM users (CIS.1.4 / FSBP.IAM.7)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-3b--mfa-on-root--iam-users-cis14--fsbpiam7).
> get-account-summary MFA probe (jq filter on AccountMFAEnabled).

**Verdict signals:**
- `AccountMFAEnabled = 0` → root has no MFA. **ROOT_CAUSE_FOUND**,
  `LAYER: IAM_MFA`.
- `MFADevicesInUse < sum of active users with console login` → at
  least one IAM user lacks MFA. **ROOT_CAUSE_FOUND**, `LAYER: IAM_MFA`.
  Drill down with `aws iam list-virtual-mfa-devices` and the
  credential report.

#### 3c: Aged access keys (CIS.1.3 / FSBP.IAM.6)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-3c--aged-access-keys-cis13--fsbpiam6).
> get-credential-report base64/awk aged-key extraction pipeline.

**Verdict signals:**
- Any active key with `access_key_1_last_rotated` older than 90 days
  → **ROOT_CAUSE_FOUND**, `LAYER: IAM_PASSWORD_POLICY` (key-rotation
  sub-layer). Remediation: `aws iam update-access-key` (deactivate)
  and `aws iam create-access-key` (rotation).

### Step 4: EC2 controls

#### 4a: IMDSv2 required (EC2.8 / FSBP.EC2.8)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-4a--imdsv2-required-ec28--fsbpec28).
> describe-instances MetadataOptions probe (HttpTokens optional vs required).

**Verdict signals:**
- `HttpTokens=optional` → **ROOT_CAUSE_FOUND**, `LAYER: EC2_IMDSV2`.
  Remediation: `aws ec2 modify-instance-metadata-options
  --http-tokens required`.

#### 4b: Security group 0.0.0.0/0 (EC2.2 / EC2.4 / PCI.EC2.2-4)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-4b--security-group-00000-ec22--ec24--pciec22-4).
> describe-security-groups 0.0.0.0/0 ingress probe.

**Verdict signals:**
- SG rule allows `0.0.0.0/0` on ports 22, 3389, 3306, etc. →
  **ROOT_CAUSE_FOUND**, `LAYER: EC2_SG`. Remediation:
  `aws ec2 revoke-security-group-ingress` then add a scoped rule.

### Step 5: KMS key rotation (KMS.3 / PCI.KMS.1)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-5--kms-key-rotation-kms3--pcikms1).
> kms describe-keys EnableKeyRotation probe.

**Verdict signals:**
- `EnableKeyRotation=false` on a customer-managed CMK →
  **ROOT_CAUSE_FOUND**, `LAYER: KMS_ROTATION`. Remediation:
  `aws kms enable-key-rotation --key-id <key-id>`.

### Step 6: CloudTrail data events (CloudTrail.4 / CIS.2.7)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-6--cloudtrail-data-events-cloudtrail4--cis27).
> describe-trails + get-event-selectors probes.

**Verdict signals:**
- No event selector with `IncludeManagementEvents=true` AND
  `ReadWriteType=All` AND `DataResources` covering `s3:::` or
  `lambda:::` → **ROOT_CAUSE_FOUND**,
  `LAYER: CLOUDTRAIL_DATA_EVENTS`. Remediation:
  `aws cloudtrail put-event-selectors`.

### Step 7: Config recorder coverage (Config.1)

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-7--config-recorder-coverage-config1).
> describe-configuration-recorders + describe-delivery-channels probes.

**Verdict signals:**
- Recorder `status` is not recording, or `recordingGroup.allSupported=false`
  → **ROOT_CAUSE_FOUND**, `LAYER: CONFIG_RECORDER`. Remediation:
  `aws configservice start-configuration-recorder` and update the
  recording group.

### Step 8: `NOT_AVAILABLE` with StatusReasons

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-8--not_available-statusreasons-read).
> jq extraction of Compliance.StatusReasons from the finding JSON.

**Common ReasonCodes:**

| Code | Meaning | Action |
|---|---|---|
| `CONFIG_NO_EVALUATIONS` | Config rule has not run yet | Wait 5-30 min for the first eval cycle. |
| `CONFIG_RULE_NOT_APPLICABLE` | Resource is out of scope (e.g., Lambda control, no Lambda in account) | Suppress via Automation Rule or accept as permanent NOT_AVAILABLE. |
| `CONFIG_EVALUATION_ERROR` | The Config rule Lambda errored | Inspect the rule's CloudWatch Logs; fix the Lambda. |
| `INSUFFICIENT_DATA` | Config has no data for the resource | Verify the recorder covers the resource type and region. |

**Verdict signals:**
- ReasonCode maps to a transient state (first eval, aggregation lag)
  → **NEED_MORE_INFO**, `LAYER: AWS_SIDE`. Wait and re-check.
- ReasonCode maps to a permanent gap (Lambda-backed rule broken,
  resource out of scope) → **ROOT_CAUSE_FOUND**,
  `LAYER: AWS_SIDE` or `LAYER: FALSE_POSITIVE`.

### Step 9: Stuck `RESOLVED`-but-still-appearing

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-9--stuck-resolved-but-still-appearing).
> Security Hub workflow/compliance state vs Config resource-history comparison probes.

**Verdict signals:**
- Security Hub `Workflow.Status=RESOLVED`, `Compliance.Status=PASSED`,
  Config shows the fix is in place → the finding is in the 3-5 day
  archive window. **ROOT_CAUSE_FOUND**, `LAYER: FALSE_POSITIVE` (will
  auto-archive).
- Security Hub `RESOLVED` but `Compliance.Status=FAILED` on re-eval →
  the resource was reverted, or a second resource of the same type
  triggered a new finding. **ROOT_CAUSE_FOUND** at the failing
  resource layer.

### Step 10: Cross-account aggregation gap

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-10--cross-account-aggregation-gap).
> Aggregator-side get-finding-aggregator/list-members and member-side get-administrator-account probes.

**Verdict signals:**
- Aggregator exists but member account not in `list-members` →
  **ROOT_CAUSE_FOUND**, `LAYER: AGGREGATOR_GAP`. Remediation:
  re-invite the member via `create-members`.
- Member account's administrator doesn't match the aggregator →
  the member was re-invited by a different administration account
  (common after an org reshuffle). **ROOT_CAUSE_FOUND**,
  `LAYER: AGGREGATOR_GAP`.

### Step 11: Custom action wired but not firing

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-11--custom-action-wired-but-not-firing).
> EventBridge rule/target, Lambda resource policy, and test-event-pattern probes.

**Verdict signals:**
- EventBridge rule exists, target set, but `test-event-pattern` returns
  `Result: false` → the event pattern doesn't match the ASFF finding
  shape. **ROOT_CAUSE_FOUND**, `LAYER: CUSTOM_ACTION_GAPPED`.
- EventBridge matches, but Lambda permission missing
  `events:aws:SourceArn` condition or the target ARN is wrong →
  **ROOT_CAUSE_FOUND**, `LAYER: CUSTOM_ACTION_GAPPED`.

### Step 12: Automation Rules not applying

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#step-12--automation-rules-not-applying).
> list-automation-rules and get-automation-rules probes.

**Verdict signals:**
- Rule exists with `Criteria.SeverityLabel` not matching the finding's
  `Severity.Label` (e.g., rule filters on `CRITICAL` but finding is
  `HIGH`) → **ROOT_CAUSE_FOUND**,
  `LAYER: AUTOMATION_RULE_MISCONFIGURED`.
- Rule exists with `Criteria.AwsAccountId` excluding the finding's
  account → **ROOT_CAUSE_FOUND**,
  `LAYER: AUTOMATION_RULE_MISCONFIGURED`.
- Rule `IsTerminal=false` and the rule order is below another
  conflicting rule → the higher-priority rule wins. **ROOT_CAUSE_FOUND**,
  `LAYER: AUTOMATION_RULE_MISCONFIGURED`.

### Step 13: Suppression / Automation Rules — when and how

Apply suppression (lower severity or archive) only after a finding is
confirmed FALSE_POSITIVE or out of permanent scope. Use Automation
Rules (preferred 2024+) over manual `update-findings`.

> Moved to [references/control-catalogue-and-remediation.md](references/control-catalogue-and-remediation.md#step-13--suppression-cli-and-fp-class-patterns).
> create-automation-rule suppression CLI plus per-FP-class criteria (CI keys CIS.1.3, documented public bucket S3.2, sandbox EC2.8).

### Step 14: Custom actions via EventBridge → Lambda

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-14-custom-actions-via-eventbridge--lambda).
> Auto-remediation wiring: CRITICAL/HIGH FAILED import event pattern, per-layer Lambda targets, SOC-chat posting rule.

### Step 15: Escalate or NEED_MORE_INFO

If no probe produced a positive root-cause match, OR the finding
indicates an AWS-side issue (Config rule Lambda crash, aggregator
outage), emit:

- **ESCALATE** — AWS-side incident or compliance gap beyond the
  operator's scope (Config rule Lambda broken cross-region, Security
  Hub service event). Surface the AWS Health event ARN, finding ID,
  and AWS Support case recommendation.
- **NEED_MORE_INFO** — A probe requires operator input (cross-account
  assume-role missing, member account inaccessible, Config recorder
  disabled). List the missing pieces and the next probe to run once
  available.

## NEVER (top 5)

- **NEVER declare ROOT_CAUSE_FOUND without corroborating evidence from
  the service CLI or Config.** A Security Hub finding is a control
  evaluation, not ground truth. The resource's actual state — confirmed
  via `s3api` / `iam` / `ec2` / `kms` / `cloudtrail` — must match the
  control failure.

- **NEVER suppress a finding family with a blanket Automation Rule.**
  Suppressing all `CIS.1.3*` or all `EC2.8*` hides real failures.
  Scope suppression to a specific resource, account, or principal via
  Automation Rule criteria.

- **NEVER treat `NOT_AVAILABLE` as compliant.** It means the Config
  rule could not evaluate. The resource is in an unknown state —
  investigate `Compliance.StatusReasons` and either fix the rule or
  scope the resource before clearing.

- **NEVER trust a `RESOLVED` finding that immediately re-fails.** A
  finding that flips RESOLVED → FAILED within 30 min indicates a race
  or a second resource of the same type. Verify with Config resource
  history before closing.

- **NEVER disable a standard mid-audit without expecting stale
  findings.** Disabling stops new evaluations but does NOT clear
  existing findings — they remain ACTIVE for 3-5 days. Explicitly
  suppress or update workflow status to clear immediately.

## Expert heuristic

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic).
> Three triage questions: status-vs-actual-state, account/region locality, rule health — all three true means real control failure.

## Output format

See **STRICT output contract** above. Every investigation emits exactly
one diagnostic block per finding. A CONFIRMATION gate precedes any
state-changing CLI.

### Worked example — S3.1 public access finding

```text
FINDING: arn:aws:securityhub:us-east-1:111:finding/abc (S3.1 on customer-data-prod)
VERDICT: ROOT_CAUSE_FOUND
REASON: The account-level S3 Public Access Block has
  RestrictPublicBuckets=false, and the bucket has a public-read ACL
  applied by a legacy deployment script. The control S3.1 correctly
  evaluates FAILED (Step 2a).
LAYER: S3_BPA
SEVERITY: HIGH
STANDARD: FSBP
EVIDENCE:
  - Security Hub finding: GeneratorId contains "S3.1",
    Resources[0].Id = arn:aws:s3:::customer-data-prod,
    Compliance.Status = FAILED, Severity.Label = HIGH.
  - Probe: aws s3control get-public-access-block returns
    RestrictPublicBuckets=false, IgnorePublicAcls=false.
  - Probe: aws s3api get-bucket-acl shows AllUsers READ grant.
  - FP ruled out: bucket is NOT a documented public website (no
    CloudFront, no signed-URL pattern, S3 access logs show corporate
    IPs only — not a public consumer pattern).
SUPPRESSION: Not applicable — true control failure.
REMEDIATION:
  1. Lock down the account-level BPA:
     aws s3control put-public-access-block --account-id 111 \
       --public-access-block-configuration \
       BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  2. Remove the public ACL: aws s3api put-bucket-acl --bucket
     customer-data-prod --acl private
  3. Verify: get-findings on S3.1 returns Compliance.Status=PASSED
     within 5-30 min of the next eval cycle.
CONFIRM: "CONFIRM: About to put-public-access-block on account 111 and
  remove the public ACL on customer-data-prod. Proceed? (yes/no)"
```

### Worked example — CIS.1.3 NOT_AVAILABLE StatusReason

> Moved to [references/worked-examples.md](references/worked-examples.md#worked-example--cis13-not_available-statusreason).
> ROOT_CAUSE_FOUND / LAYER AWS_SIDE block: rule-Lambda missing iam:GetCredentialReport, fix plus re-evaluation.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Mindset, Step 0 non-obvious behaviours, Step 14 auto-remediation wiring, expert heuristic, recent AWS features
- [control-catalogue-and-remediation](references/control-catalogue-and-remediation.md) — control catalogue, severity mapping, Automation Rule criteria, Step 13 suppression CLI and FP-class patterns
- [diagnostic-commands](references/diagnostic-commands.md) — account-wide pre-flight plus every per-step corroborating probe (Steps 2-12)
- [worked-examples](references/worked-examples.md) — CIS.1.3 NOT_AVAILABLE worked example

## Domain

AWS CloudOps / Security Hub Control Diagnosis, Compliance Standard
Mapping (CIS, PCI DSS, FSBP, NIST 800-53), Service-Level Remediation,
and Custom Action / Automation Rule Configuration.

## Recent AWS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> Automation Rules GA, custom controls, central configuration, FSBP expansion (Bedrock/Q/SageMaker), cross-region aggregation, Resilience Hub, Inspector dedup.

## AWS documentation

- **Security Hub User Guide** — https://docs.aws.amazon.com/securityhub/latest/userguide/
- **Security Hub controls reference** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-controls-reference.html
- **CIS / PCI / FSBP / NIST controls** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-controls-reference.html
- **Security Hub Automation Rules** — https://docs.aws.amazon.com/securityhub/latest/userguide/automation-rules.html
- **Security Hub ASFF** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-findings-format.html
- **AWS CLI Security Hub reference** — https://docs.aws.amazon.com/cli/latest/reference/securityhub/
