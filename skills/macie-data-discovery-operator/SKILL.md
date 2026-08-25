---
name: macie-data-discovery-operator
description: 'Operates Amazon Macie data discovery lifecycle — enables Macie (org-level delegated admin), creates classification jobs (one-time vs scheduled, S3 scope), configures managed data identifiers (PII, financial, credentials), creates custom data identifiers (Regex patterns), manages findings (policy:IAMUser/S3, sensitiveData:S3Object), configures suppression rules, enables automated ML-based discovery, integrates with Security Hub, wires Lambda / Step Functions for auto-remediation. Runs deterministic pre-checks (Macie enabled, delegated admin, S3 scope, IAM), emits exact CLI behind a CONFIRM gate, verifies post-apply state. Emits a verdict (READY | BLOCKED | COMPLETED) per operation. Use when enabling Macie, creating classification jobs, writing custom regex identifiers, suppressing findings, forwarding to Security Hub, or building PII auto-remediation. Triggers: enable Macie, delegated admin, classification job, custom data identifier, Macie findings, Security Hub, automated discovery, remediation Lambda.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live operations: AWS CLI v2 with macie2, s3, iam, sts, securityhub, lambda, and stepfunctions access. Works with Terraform aws_macie2_account / aws_macie2_classification_job / aws_macie2_custom_data_identifier resources and CloudFormation AWS::Macie::* templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, macie, security, cloudops, operate, data-discovery, pii-detection, classification, remediation, security-hub, sensitive-data
  dependencies: aws-orchestrator
  keywords: aws, macie, data discovery, cloudops, operate, classification, pii, managed data identifiers, custom data identifiers, regex, findings, suppression rules, automated discovery, security hub, lambda remediation, step functions, delegated admin, s3 scanning, sensitive data, data loss prevention
  when_to_use: Invoke when the user wants to enable Macie (standalone or org-level delegated admin), create or manage classification jobs (one-time or scheduled), configure managed data identifiers, create custom regex-based data identifiers, manage findings (policy or sensitive-data types), configure suppression rules, enable automated ML-based discovery, forward findings to Security Hub, wire Lambda or Step Functions for auto-remediation of exposed PII, or aggregate cross-account Macie findings. Do NOT invoke for Amazon GuardDuty threat detection, AWS Config rule evaluation, or Security Hub control management (use guardduty-finding-triage or securityhub-finding-triage).
---

# Macie Data Discovery Operator

An AWS CloudOps agent skill that operates Amazon Macie data discovery
lifecycle operations correctly and safely. Runs deterministic pre-checks
before any state-changing CLI, emits the exact CLI behind a CONFIRM gate,
and verifies state transitions after apply.

## What this skill does

Executes Macie lifecycle operations: enabling Macie (standalone or
org-level delegated admin), creating classification jobs (one-time or
scheduled), configuring managed and custom data identifiers, managing
findings and suppression rules, enabling automated ML-based discovery,
integrating with Security Hub, and wiring Lambda/Step Functions for
auto-remediation. Every operation surfaces finding scope, detection
coverage, and remediation posture.

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
OPERATION: <enable | classify | custom-id | findings | suppress | auto-discovery | security-hub | remediate | aggregate>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <macie-resource-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> on <target> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <job status / finding state / Macie status after apply>
NOTES: <detection coverage rationale, finding severity, remediation caveats>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble ("Let me analyze…") — the
  VERDICT block is the FIRST line, always. Use uppercase verdict values
  only (`READY`, `BLOCKED`, `COMPLETED`).
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or
  `[FAIL]` and a specific reason for each failure.
- NEVER emit a CLI command with placeholder flags in a READY plan —
  every flag must be populated with actual values from the input data.
- NEVER claim COMPLETED without every POST_VERIFY line showing `[PASS]`,
  and never omit the CONFIRM gate as the first STEPS entry for
  state-changing operations.
- NEVER classify as READY if Macie is not enabled in the target account
  or region — Macie operations fail silently without enablement.

## Quick navigation

| Section | When to read |
|---|---|
| §"Mindset" | Understanding the Macie detection model |
| §"Pre-flight" | Macie enablement + delegated admin gate |
| §"Step 1 — Enable Macie" | Org-level delegated admin setup |
| §"Step 2 — Classification jobs" | One-time vs scheduled S3 scanning |
| §"Step 3 — Managed data identifiers" | PII / financial / credential types |
| §"Step 4 — Custom data identifiers" | Regex-based detection |
| §"Step 5 — Findings management" | Policy and sensitive-data findings |
| §"Step 6 — Suppression rules" | False-positive filtering |
| §"Step 7 — Automated discovery" | ML-based continuous scanning |
| §"Step 8 — Security Hub integration" | Findings forwarding |
| §"Step 9 — Auto-remediation" | Lambda + Step Functions |
| §"NEVER do these things" | Review before risky operations |
| §"Output format" | Structured output template |
| references/detection-and-remediation.md | Deep identifier + remediation patterns |
| references/operating-cli-commands.md | Copy-pasteable CLI sequence |

## Mindset

Three Macie realities drive every operation:

→ Extended Mindset rationale moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Pre-flight: Macie enablement + delegated admin gate

Run before any operation. `get-macie-session` returns the Macie
enablement status. `get-administrator-account` returns the delegated
admin (org-level).

→ Live-account pre-flight command listing moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Attribute | Effect on operation |
|---|---|
| Macie `status: PAUSED` | Classification jobs do not run. Findings not published. Re-enable via `enable-macie-session`. |
| Delegated admin not set | Org-level operations (cross-account) fail. Must delegate admin first. |
| No existing classification job | New job creation is safe. |
| Bucket not in Macie account | `s3:Bucket*` permissions needed for Macie service role. |
| `findingPublishingFrequency` unset | Defaults to 15 min. Critical findings may delay. |

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

## Expert heuristic: finding severity and detection coverage

→ Expert-heuristic deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## 10-step operating procedure

### Step 1 — Enable Macie (standalone or org-level delegated admin)

Macie must be enabled before any other operation.

**Standalone (single account):**

```bash
aws macie2 enable-macie-session \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --status ENABLED
```

**Org-level delegated admin:**

```bash
# 1. Designate the admin account (run in management account)
aws macie2 enable-organization-admin-account \
  --admin-account-id 123456789012

# 2. In the delegated admin account, enable Macie for the org
aws macie2 enable-macie-session \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --status ENABLED

# 3. Configure auto-enable for new member accounts
aws macie2 update-organization-configuration \
  --auto-enable true
```

**Common mistake:** enabling Macie in the management account instead of
delegating to a dedicated security admin account. Org-level Macie
should use a designated admin account that manages all member accounts.

### Step 2 — Classification jobs (one-time vs scheduled)

Classification jobs scan S3 buckets for sensitive data.

**One-time job:**

```bash
aws macie2 create-classification-job \
  --name "pii-scan-2026-08" \
  --job-type ONE_TIME \
  --s3-job-definition \
    bucketDefinitions='[{accountId=123456789012,buckets=[prod-data-bucket,financial-records]}]' \
  --managed-data-identifier-selector-ids \
    USA_SOCIAL_SECURITY_NUMBER USA_PASSPORT_NUMBER CREDIT_CARD_NUMBER \
    EMAIL_ADDRESS PHONE_NUMBER \
  --description "One-time PII scan of production data buckets"
```

**Scheduled job (CRON):**

```bash
aws macie2 create-classification-job \
  --name "weekly-pii-scan" \
  --job-type SCHEDULED \
  --schedule-frequency '{dailySchedule:{}}' \
  --s3-job-definition \
    bucketDefinitions='[{accountId=123456789012,buckets=[prod-data-bucket]}]' \
  --managed-data-identifier-selector ALL \
  --description "Weekly scheduled PII scan"
```

**Schedule options:**
- `{dailySchedule:{}}` — runs daily.
- `{weeklySchedule:{dayOfWeek=WEDNESDAY}}` — runs weekly.
- `{monthlySchedule:{dayOfMonth=15}}` — runs monthly.

**Common mistake:** not scoping the S3 bucket list. A job scanning ALL
buckets is expensive and noisy. Scope to specific buckets or use bucket
criteria (tags, prefixes) for targeted scanning.

### Step 3 — Managed data identifiers (PII, financial, credentials)

Macie provides ~150+ managed data identifiers. Select relevant
identifiers per region and data type.

**Categories:**
- **PII:** SSN, passport, driver's license, national ID (region-specific).
- **Financial:** credit card numbers, bank account, SWIFT codes.
- **Credentials:** AWS access keys, private keys, API tokens.
- **Personal:** email, phone, address, name, date of birth.

**Selection strategies:**

```bash
# Option A: ALL managed identifiers (comprehensive, expensive)
--managed-data-identifier-selector ALL

# Option B: Specific identifiers (targeted, cost-efficient)
--managed-data-identifier-selector-ids \
  USA_SOCIAL_SECURITY_NUMBER USA_PASSPORT_NUMBER CREDIT_CARD_NUMBER

# Option C: RECOMMENDED (Macie selects based on bucket content sampling)
--managed-data-identifier-selector RECOMMENDED
```

**Common mistake:** using ALL for every job. This scans for 150+
identifiers including region-irrelevant ones (e.g., scanning for UK NINO
on US-only data). Use RECOMMENDED or select specific identifiers.

### Step 4 — Custom data identifiers (regex patterns)

Custom identifiers detect organization-specific data formats via regex.

```bash
aws macie2 create-custom-data-identifier \
  --name "employee-id-pattern" \
  --regex "EMP[0-9]{6}" \
  --keywords "employee" "emp_id" "staff" \
  --ignore-words "example" "test" "sample" \
  --maximum-match-distance 50 \
  --severity-levels HIGH \
  --description "Detects EMP###### employee ID format"
```

**Key parameters:**
- `--regex`: the PCRE-compatible regex pattern.
- `--keywords`: proximity keywords — Macie only reports matches near
  these keywords (reduces false positives).
- `--ignore-words`: words to exclude from matches (test data, examples).
- `--maximum-match-distance`: max character distance between the regex
  match and a keyword for the finding to be reported.

**Common mistake:** omitting `--keywords`. Without keywords, every
regex match is reported, generating massive false positives. Always
scope with proximity keywords.

### Step 5 — Findings management

Macie publishes findings to the Macie console and (optionally) Security
Hub and EventBridge.

**List and filter findings:**

```bash
# All high-severity findings in the last 7 days
aws macie2 list-findings \
  --finding-criteria \
    criterion='{severity:{eq:[HIGH]},createdAt:{gte:"2026-08-03T00:00:00Z"}}' \
  --output json

# Get finding details
aws macie2 get-findings --finding-ids <finding-id-1> <finding-id-2>
```

**Finding types:**
- `policy:IAMUser/S3/BucketPublic` — publicly accessible bucket.
- `policy:IAMUser/S3/BucketSharedExternally` — shared with external
  account.
- `sensitiveData:S3Object/<Identifier>` — sensitive data detected.

**Archiving findings (soft delete):**

```bash
aws macie2 update-findings \
  --finding-ids <finding-id> \
  --status ARCHIVED
```

### Step 6 — Finding suppression rules

Suppression rules auto-archive findings matching criteria (reduces
noise from known false positives or accepted-risk patterns).

```bash
aws macie2 put-findings-filter \
  --name "suppress-test-bucket-findings" \
  --action '{archived:true}' \
  --finding-criterion \
    criterion='{resource.tags.tagKey: {eq: [Environment]}, resource.tags.tagValue: {eq: [test]}}' \
  --description "Auto-archive findings on test-environment buckets"
```

**Common mistake:** overly broad suppression rules. Suppressing all
findings on a bucket prefix that also contains production data masks
real risks. Scope suppression rules tightly (specific tags, specific
finding types).

### Step 7 — Automated ML-based discovery (latest feature)

Automated discovery uses ML to continuously scan all S3 buckets without
requiring manual classification jobs.

```bash
# Enable automated discovery
aws macie2 update-automated-discovery-configuration \
  --status ENABLED \
  --auto-enable-members true \
  --scope ONE_TO_ONE_MEMBERS
```

**Benefits:**
- ML-based: adapts to bucket content without explicit identifier
  selection.
- Continuous: scans all new and modified objects automatically.
- No job management: no need to create and schedule classification jobs.

**Limitations:**
- Still has scan frequency (not instant) — objects are queued.
- Does NOT replace custom identifiers for organization-specific patterns.
- Costs more than targeted classification jobs (scans all S3).

**Common mistake:** enabling automated discovery and deleting all
classification jobs. Automated discovery and classification jobs serve
different purposes — keep targeted jobs for specific high-risk buckets.

### Step 8 — Macie + Security Hub integration

Forward Macie findings to Security Hub for centralized security posture.

```bash
# Enable Security Hub integration
aws macie2 put-classification-export-configuration \
  --configuration '{securityHubConfiguration:{enableSecurityHubIntegration:true}}'

# Verify
aws macie2 get-classification-export-configuration
```

**Behavior:**
- Macie forwards findings to Security Hub as `AWS::Macie::Finding`
  resources.
- Security Hub deduplicates, correlates, and aggregates with other
  security findings.
- Finding severity maps to Security Hub severity (High, Medium, Low).

**Common mistake:** not enabling Security Hub before Macie integration.
Macie integration fails if Security Hub is not enabled in the account.

### Step 9 — Macie + Lambda / Step Functions auto-remediation

Wire Macie findings to EventBridge → Lambda or Step Functions for
auto-remediation (e.g., quarantine public PII, restrict bucket ACL).

**EventBridge rule (Macie findings → Lambda):**

```bash
aws events put-rule \
  --name "macie-finding-trigger" \
  --event-pattern '{
    "source": ["aws.macie"],
    "detail-type": ["Macie Finding"],
    "detail": {
      "severity": ["High", "Critical"]
    }
  }'

# Lambda target for remediation
aws events put-targets \
  --rule "macie-finding-trigger" \
  --targets '[{"Id":"macie-remediation-lambda","Arn":"arn:aws:lambda:us-east-1:123456789012:function:macie-remediate"}]'
```

**Step Functions workflow (multi-step remediation):**

```bash
aws stepfunctions create-state-machine \
  --name "macie-remediation-workflow" \
  --definition file://remediation-workflow.json \
  --role-arn arn:aws:iam::123456789012:role/MacieRemediationRole
```

The Step Functions workflow can: (1) parse finding details, (2) check
bucket exposure, (3) quarantine object (move to isolated bucket or
encrypt), (4) restrict bucket ACL, (5) notify security team via SNS.

**Common mistake:** not scoping the Lambda/Step Functions remediation to
specific finding types. A blanket "restrict all buckets on any finding"
rule can break production applications. Scope to specific finding types
(e.g., `sensitiveData:S3Object/Credit_Card` on public buckets only).

### Step 10 — Cross-account findings aggregation

For org-level Macie deployments, aggregate findings from all member
accounts into the delegated admin account.

```bash
# In the delegated admin account, list all member accounts
aws macie2 list-members \
  --query 'members[*].[accountId,relationshipStatus]' \
  --output text

# Query findings across all member accounts
aws macie2 list-findings \
  --finding-criteria \
    criterion='{severity:{eq:[HIGH,CRITICAL]}}'
```

**Common mistake:** not verifying member account relationship status.
Accounts in `Paused` or `Enabled` (but not `Invited`/`Accepted`) do not
forward findings. Verify `relationshipStatus=Enabled` for all members.

## NEVER do these things (top 5)

1. **NEVER create a classification job without verifying Macie is
   enabled.** Classification jobs fail silently if Macie is disabled or
   paused. Run `get-macie-session` first.

2. **NEVER use `--managed-data-identifier-selector ALL` for every job.**
   This scans for 150+ identifiers including region-irrelevant ones,
   increasing cost and false positives. Use RECOMMENDED or select
   specific identifiers.

3. **NEVER create custom data identifiers without `--keywords`.** Without
   proximity keywords, every regex match is reported — massive false
   positives. Always scope with keywords and `--maximum-match-distance`.

4. **NEVER enable auto-remediation Lambda without scoping by finding
   type.** A blanket "restrict all buckets on any finding" rule breaks
   production applications. Scope to specific finding types and
   severities.

5. **NEVER suppress findings without documenting the risk acceptance.**
   Suppression rules auto-archive findings. An undocumented suppression
   on a production bucket masks real risks. Document the suppression
   rationale in the filter description.

**Additional critical mistakes:** never enable Macie in the management
account for org-level (use delegated admin); never enable automated
discovery and delete all classification jobs (keep targeted jobs for
high-risk buckets); never forward findings to Security Hub without
enabling Security Hub first; never create overly broad suppression rules
(scope tightly by tags and finding types); never forget to configure
`findingPublishingFrequency` (defaults to 15 min, critical findings may
delay).

## Output format

→ Literal output template moved verbatim to [references/worked-examples.md](references/worked-examples.md); the STRICT output contract above carries the authoritative template.

### Worked example — create classification job (READY)

```text
OPERATION: classify
VERDICT: READY
TARGET: weekly-pii-scan
PRE_CHECKS:
  - [PASS] Macie session ENABLED (get-macie-session status=ENABLED)
  - [PASS] Target bucket prod-data-bucket exists in account 123456789012
  - [PASS] Managed identifier IDs valid (USA_SOCIAL_SECURITY_NUMBER etc.)
  - [PASS] IAM role has macie2:CreateClassificationJob permission
STEPS:
  1. CONFIRM: About to create a scheduled classification job weekly-pii-scan on bucket prod-data-bucket in account 123456789012 region us-east-1. This will scan for managed PII identifiers daily. Proceed? (yes/no)
  2. aws macie2 create-classification-job --name weekly-pii-scan --job-type SCHEDULED --schedule-frequency '{dailySchedule:{}}' --s3-job-definition bucketDefinitions='[{accountId=123456789012,buckets=[prod-data-bucket]}]' --managed-data-identifier-selector RECOMMENDED --description "Daily PII scan of production data bucket"
POST_VERIFY: (pending execution)
STATE: pending — will be RUNNING after creation, COMPLETE after first scan
NOTES: RECOMMENDED selector lets Macie sample bucket content and select relevant identifiers. Job runs daily. Findings published at FIFTEEN_MINUTES frequency. For organization-specific data formats, create custom data identifiers separately.
```

### Worked example — Macie not enabled (BLOCKED)

→ Secondary worked example moved verbatim to [references/worked-examples.md](references/worked-examples.md).

## Expert heuristic: detection coverage gap analysis

→ Expert-heuristic deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

→ Recent AWS features deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — expert-heuristic deep dives, extended Mindset rationale, recent AWS features 2024-2026
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight command listing
- [references/worked-examples.md](references/worked-examples.md) — secondary worked example (BLOCKED) and the literal output-format template
- [references/detection-and-remediation.md](references/detection-and-remediation.md) — deep identifier + remediation patterns (identifier categories, suppression, auto-remediation)
- [references/operating-cli-commands.md](references/operating-cli-commands.md) — copy-pasteable CLI sequence for every operating step

## Domain

AWS CloudOps / Amazon Macie Data Discovery & Sensitive Data Protection.

## AWS documentation

- **Amazon Macie User Guide** — https://docs.aws.amazon.com/macie/latest/user/what-is-macie.html
- **Macie managed data identifiers** — https://docs.aws.amazon.com/macie/latest/user/managed-data-identifiers.html
- **Macie custom data identifiers** — https://docs.aws.amazon.com/macie/latest/user/custom-data-identifiers.html
- **Macie classification jobs** — https://docs.aws.amazon.com/macie/latest/user/classification-jobs.html
- **Macie findings** — https://docs.aws.amazon.com/macie/latest/user/findings.html
- **Macie + Security Hub** — https://docs.aws.amazon.com/macie/latest/user/securityhub-integration.html
- **Macie automated discovery** — https://docs.aws.amazon.com/macie/latest/user/automated-discovery.html
- **Macie API Reference** — https://docs.aws.amazon.com/macie/latest/APIReference/
