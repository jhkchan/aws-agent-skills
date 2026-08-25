---
name: accessanalyzer-finding-triage
description: 'Triages IAM Access Analyzer findings (external access + unused access) into risk verdicts with remediation. Classifies each finding as real external exposure (EXTERNAL_ACCESS), stale credential or permission (UNUSED_ACCESS), expected cross-account or service integration (EXPECTED), or condition-bounded non-risk (SAFE). Evaluates the zone-of-trust model, principal type (public vs specific vs service), condition-key cryptographic strength, resource-type blast radius, and finding freshness. INVOKE DETERMINISTICALLY when the input contains an Access Analyzer finding JSON or finding reference — detection signal: findingType is ExternalAccess or starts with Unused, OR the input references isPublic, zone of trust, resource-based policy exposure, archive rule, or UnusedIAMRole/UnusedIAMUserAccessKey. Use when reviewing Access Analyzer findings, triaging external-access or unused-access findings, prioritizing remediation, or validating archive-rule suppression decisions.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf). No AWS CLI required for offline finding classification. Live-account triage uses aws accessanalyzer list-findings and aws accessanalyzer archive-rule (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: EXTERNAL_ACCESS | UNUSED_ACCESS | EXPECTED | SAFE
  pattern: Mindset → Quick Triage → Expert Deltas → Process → Matrices → Anti-Patterns → Pre-flight Gate → Remediation
  when_to_use: Reviewing IAM Access Analyzer findings, triaging external-access or unused-access findings, prioritizing which findings to remediate first, validating whether a finding can be archived, or deciding if a cross-account resource-policy grant is an expected integration or a security risk.
  version: 0.2.0
  author: Jacky Chan — AWS Community Builder
  keywords: IAM Access Analyzer, external access, unused access, finding triage, zone of trust, isPublic, cross-account, resource-based policy, archive rule, UnusedIAMRole, unused access key, KMS key policy, S3 bucket policy, SQS queue policy, Secrets Manager, IAM role trust, condition strength, aws:SourceArn, aws:SourceAccount, service principal
  tags: iam, security, access-analyzer, finding-triage, external-access, unused-access, zone-of-trust
---

# IAM Access Analyzer Finding Triage

**Structural pattern:** Mindset → Quick Triage → Expert Deltas → Process → Matrices → Anti-Patterns → Pre-flight Gate → Remediation. Read top-to-bottom; the Quick Triage section is sufficient for 80% of findings. Descend into Process and Matrices only for edge cases.

## Mindset

Full framing (what Access Analyzer evaluates, real-risk vs expected-integration vs condition-bounded contrast): [Advanced patterns](references/advanced-patterns.md).

The triage must distinguish:

1. **Real risk** (EXTERNAL_ACCESS) — unconditional access to a principal
   outside the zone of trust, or a public principal with no restrictive
   condition.
2. **Stale identity** (UNUSED_ACCESS) — an IAM role, user credential, or
   permission grant that has not been used in the analysis period.
3. **Expected integration** (EXPECTED) — a known cross-account or AWS-service
   integration that Access Analyzer correctly flagged but the business has
   accepted. These should be archived via an archive rule, not ignored.
4. **Condition-bounded** (SAFE) — the finding is technically valid but a
   cryptographic condition (`aws:SourceArn`, `aws:SourceAccount`) makes the
   access non-exploitable by the external principal.

## Quick triage (TL;DR decision flow)

This compact flow handles the majority of findings. For edge cases,
descend into the full Process section below.

```
INPUT: Access Analyzer finding JSON
  │
  ├─ findingType missing or unparseable? ──────────────────────► ERROR
  │
  ├─ findingType starts with "Unused"? ────────────────────────► Step 1B
  │                                                              (unused-access path)
  │
  ├─ status is RESOLVED or ARCHIVED? ──────────────────────────► SAFE
  │  (finding is no longer active — stop here)
  │
  ├─ CONDITION strength check (the primary verdict lever):
  │  ├─ aws:SourceArn (concrete ARN, StringEquals)  ──────────► SAFE
  │  ├─ aws:SourceArn (wildcard pattern, StringLike) ─────────► SAFE (note breadth)
  │  ├─ aws:SourceAccount (specific account ID)     ──────────► SAFE
  │  ├─ aws:PrincipalOrgID (own org)                ──────────► SAFE
  │  ├─ aws:SourceVpce / aws:SourceVpc (no IGW)     ──────────► SAFE
  │  ├─ kms:ViaService                              ──────────► SAFE (KMS only)
  │  ├─ aws:SourceIp = 0.0.0.0/0                    ──────────► NOT SAFE (= no condition)
  │  ├─ aws:Referer / aws:UserAgent                 ──────────► NOT SAFE (forgeable)
  │  └─ absent or {}                                ──────────► NOT SAFE (proceed to principal)
  │
  ├─ PRINCIPAL check (when condition is weak/absent):
  │  ├─ {"Service": "xxx.amazonaws.com"} + matches Expected table ─► EXPECTED
  │  ├─ {"Service": "xxx.amazonaws.com"} + destructive actions     ─► EXTERNAL_ACCESS
  │  ├─ {"Federated": same-account IdP}               ──────────► EXPECTED
  │  ├─ {"Federated": external-account IdP}           ──────────► EXTERNAL_ACCESS (HIGH)
  │  ├─ arn:aws:iam::EXTERNAL_ACCOUNT:root (no cond)  ──────────► EXTERNAL_ACCESS
  │  └─ Principal "*" or {"AWS": "*"} (no cond)       ──────────► EXTERNAL_ACCESS
  │
  └─ RISK assigned via Resource-type severity matrix (Step 1A.5)
```

**Three rules that prevent the most common misclassifications:**

Full wording of the three misclassification rules: [Advanced patterns](references/advanced-patterns.md).

## Expert knowledge deltas (non-obvious thresholds)

These are insights that a senior CloudOps engineer learns from production
incidents, not from the AWS documentation. Internalize them before triaging.

All eight expert deltas — identity-policy blind spot, `isPublic` algorithm, `StringEquals` vs `StringLike`, `kms:CreateGrant` chain, configurable analysis period, `analyzedAt` staleness, deprecated `aws:PrincipalAccount`, delegated-administrator archive rules: [Advanced patterns](references/advanced-patterns.md).

## Zone of trust model (expert concept)

Access Analyzer defines a **zone of trust** based on the analyzer type. This
determines what counts as "external" — the same resource-policy grant can be
flagged or not flagged depending on which analyzer generated the finding:

Account-analyzer vs organization-analyzer zone-of-trust table (what each flags as external): [Advanced patterns](references/advanced-patterns.md).

Analyzer-scope triage implication (account vs organization analyzer): [Advanced patterns](references/advanced-patterns.md).

Worked mini-example (same grant: EXPECTED under an account analyzer, unflagged under an org analyzer): [Worked examples](references/worked-examples.md).

## Finding types

Access Analyzer generates two categories of findings. The skill handles both
but routes them through different classification paths:

External-access finding schema (principal, `isPublic`, condition, action, resourceType), the analyzed resource-policy type catalog, and the unused-access finding-type table: [Advanced patterns](references/advanced-patterns.md).

---

## Process — Classification logic (apply in order)

### Step 0: Validate input (AWS-specific field checks)

Field-by-field requirement table (routing target and default per missing field): [Advanced patterns](references/advanced-patterns.md).

**Malformed `condition` object handling:**
Malformed-condition cases — null/non-dict, non-string values, nested operators: [Error handling](references/error-handling.md).

ERROR-verdict output block for malformed/unparseable findings: [Error handling](references/error-handling.md).

If `findingType` is `ExternalAccess` → proceed to **Step 1A** (external access
classification).

If `findingType` starts with `Unused` → proceed to **Step 1B** (unused access
classification).

### Step 1A: External access — classify by principal + condition

Apply these sub-steps in order. The **first match** determines the verdict.
The ordering is deliberate: status check first (fast-fail for resolved
findings — no point evaluating conditions on a finding that is already
closed), then condition strength (the primary verdict lever), then principal
type (only reached when the condition is weak or absent).

#### Step 1A.1: Check finding status

If `status` is `RESOLVED` or `ARCHIVED`, the finding has already been
addressed. Output:

```text
VERDICT: SAFE
REASON: Finding status is <status> — no longer an active risk. Access Analyzer re-evaluated the resource and the external-access path no longer exists (or the finding was archived).
REMEDIATION: None required. If ARCHIVED, verify an archive rule exists to suppress future instances of the same pattern.
```

If `status` is `ACTIVE`, continue.

#### Step 1A.2: Evaluate condition strength

Per-category detail (cryptographic, account-scoped, org-scoped, network-scoped, service-coupled, weak/forgeable, absent); ranked quick reference in the matrix below: [Advanced patterns](references/advanced-patterns.md).

If the condition is CRYPTOGRAPHIC, ACCOUNT-SCOPED, ORGANIZATION-SCOPED (own
org), or NETWORK-SCOPED → go to **Step 1A.3** (SAFE).

If the condition is WEAK, FORGEABLE, or ABSENT → go to **Step 1A.4** (risk
assessment).

#### Step 1A.3: Condition-bounded → SAFE

The access is cryptographically or network-bounded. The finding is valid
(Access Analyzer correctly detected the external principal), but the condition
prevents exploitation. Output:

```text
VERDICT: SAFE
RISK: LOW
REASON: Finding is valid but the condition <key> bounds access to <scope>. The external principal cannot exploit this access without the source condition being met.
REMEDIATION: No remediation required. Optionally create an archive rule to suppress future instances: filter on the same condition key + resource type.
```

#### Step 1A.4: Evaluate principal type

No restrictive condition (or weak condition). Classify by principal:

**AWS service principal** (`{"Service": "xxx.amazonaws.com"}`):
Per-principal-type classification detail (service, federated, external-account, public — including the destructive-action and known-partner exceptions): [Advanced patterns](references/advanced-patterns.md).

**Federated principal** (`{"Federated": "arn:aws:iam::ACCOUNT:saml-provider/xxx"}` or `{"Federated": "arn:aws:iam::ACCOUNT:oidc-provider/xxx"}`):

**Specific external account principal** (`arn:aws:iam::EXTERNAL_ACCOUNT:root` or specific role/user):

**Public principal** (`"*"`, `{"AWS": "*"}`):

#### Step 1A.5: Resource-type severity matrix

For EXTERNAL_ACCESS findings, assign risk based on resource type and actions:

**Risk-level mapping (emit exactly one RISK per finding):**

| Resource type | Read/List actions | Write/Modify actions | Admin/trust actions |
|---|---|---|---|
| `AWS::KMS::Key` | **CRITICAL** (decrypt = full data access) | **CRITICAL** | **CRITICAL** |
| `AWS::SecretsManager::Secret` | **CRITICAL** (credential theft) | **CRITICAL** | **CRITICAL** |
| `AWS::S3::Bucket` / `AWS::S3::AccessPoint` | **HIGH** (data exfiltration) | **CRITICAL** (data destruction / ransomware) | **CRITICAL** |
| `AWS::IAM::Role` (trust policy) | — | — | **CRITICAL** (anyone can assume the role) |
| `AWS::SQS::Queue` | **MODERATE** (message consumption) | **HIGH** (message injection / queue poisoning) | **HIGH** |
| `AWS::SNS::Topic` | **LOW** (topic metadata) | **MODERATE** (message injection) | **MODERATE** |
| `AWS::Lambda::Function` | **MODERATE** (invoke = code execution) | **HIGH** | **HIGH** |
| `AWS::EventBridge::EventBus` | **LOW** | **MODERATE** (event injection) | **MODERATE** |
| `AWS::EFS::FileSystem` | **HIGH** (file read) | **CRITICAL** (file write / ransomware) | **CRITICAL** |
| `AWS::Backup::BackupVault` | **HIGH** (backup read) | **CRITICAL** (backup deletion) | **CRITICAL** |
| Other (`AWS::OpenSearch::Domain`, `AWS::Glue::*`, etc.) | **MODERATE** | **HIGH** | **HIGH** |

**Severity escalation rules:**
- If the action set includes wildcard actions (`s3:*`, `kms:*`, `sqs:*`),
  escalate to the column for **Admin/trust actions** — wildcard includes
  deletion and configuration changes.
Escalation detail — isPublic + KMS/Secrets/S3-write → IMMEDIATE, specific-account one-level downgrade, `kms:CreateGrant` always CRITICAL: [Advanced patterns](references/advanced-patterns.md).

#### Step 1A.6: Expected service integrations reference

If the principal is a service principal AND the resource type + actions match
a row below, classify as **EXPECTED**:

Full 20-row integrations table (CloudTrail, logging, Config, Lambda, ECS, EC2, SSM, Backup, ELB, SNS, SQS, events, delivery.logs, Athena, States, GuardDuty, Security Hub, Firehose, VPN): [Advanced patterns](references/advanced-patterns.md).

If the service principal is NOT in this table, classify as EXPECTED only if
the actions are read/list or standard delivery actions (`s3:PutObject`,
`sns:Publish`, `sqs:SendMessage`, `sts:AssumeRole`). Flag for manual review
in REMEDIATION: "Unrecognized service principal — verify the AWS integration
is intentional."

### Step 1B: Unused access — classify by type and risk

#### Step 1B.1: Check finding status

Same as Step 1A.1 — if RESOLVED or ARCHIVED, output SAFE.

#### Step 1B.2: Classify by finding type and risk

Apply the unused-access risk ranking:

**UnusedIAMUserAccessKey → UNUSED_ACCESS / HIGH:**
Risk-ranking rationale for each unused-access type (credential-theft vector, MFA dependency, attack-surface expansion, scoping opportunity, governance cleanup): [Advanced patterns](references/advanced-patterns.md).
- If the user has admin-level policies attached, escalate to **CRITICAL**.

**UnusedIAMUserPassword → UNUSED_ACCESS / MODERATE:**
- Risk is **MODERATE**. Escalate to **HIGH** if MFA is not enabled for the
  user.

**UnusedIAMRole → UNUSED_ACCESS / MODERATE (default):**
- Default risk is **MODERATE**. Adjust based on the role's attached policies:
  - Role with `AdministratorAccess` or wildcard actions → **HIGH**
  - Role with read-only or scoped permissions → **MODERATE**
  - Role with write access to production resources → **HIGH**

**UnusedIAMPermission → UNUSED_ACCESS / LOW:**
- Risk is **LOW**. The remediation is to generate a scoped policy from
  CloudTrail activity (same workflow as `iam-least-privilege-advisor`).

**UnusedServiceControlPolicy → UNUSED_ACCESS / LOW:**
- An SCP that does not affect any account is a **governance cleanup** item.
- Risk is **LOW**. The SCP may be intentionally broad (deny-by-default) or
  may be a leftover from a reorganization.

#### Step 1B.3: Expected-unused patterns

The four expected-unused patterns — service-linked roles, break-glass/emergency access, cross-account audit roles, AWS-managed job-function roles: [Advanced patterns](references/advanced-patterns.md).

### Step 2: Aggregation

When triaging multiple findings, the **highest-risk finding** determines the
overall priority:

EXTERNAL_ACCESS (CRITICAL) > EXTERNAL_ACCESS (HIGH) >
UNUSED_ACCESS (HIGH) > EXTERNAL_ACCESS (MODERATE) >
UNUSED_ACCESS (MODERATE) > EXPECTED > SAFE

Group findings by resource to avoid duplicate remediation steps for the same
resource.

## Condition strength matrix (quick reference)

Ranked from strongest (non-exploitable) to weakest (no restriction):

| Rank | Condition key | Operator | Strength | Triage effect |
|---|---|---|---|---|
| 1 | `aws:SourceArn` (concrete ARN) | `StringEquals` | **Cryptographic** — AWS validates the source resource at the service layer | → SAFE |
| 2 | `aws:SourceArn` (wildcard ARN pattern) | `StringLike` | **Strong** — scoped to an account + service + region | → SAFE (note breadth) |
| 3 | `aws:SourceAccount` | any | **Account-scoped** — request must originate from the named account | → SAFE |
| 4 | `aws:PrincipalOrgID` (own org) | any | **Organization-scoped** — any principal in the org | → SAFE |
| 5 | `aws:SourceVpce` | any | **Network-scoped** — must traverse named VPC endpoint | → SAFE |
| 6 | `aws:SourceVpc` | any | **Network-scoped** — must originate in named VPC | → SAFE |
| 7 | `kms:ViaService` | any | **Service-coupled** — KMS access only through named service | → SAFE (KMS only) |
| 8 | `aws:SourceIp` (RFC1918 CIDR, no IGW) | any | **Network-scoped** — restricts to private IP range | → SAFE (caveat) |
| 9 | `aws:SourceArn` (account-level wildcard) | `StringLike` | **Weak** — `arn:aws:s3:*:*:*` has no account scoping | → NOT SAFE |
| 10 | `aws:SourceIp` (`0.0.0.0/0`) | any | **None** — entire internet | → NOT SAFE |
| 11 | `aws:Referer`, `aws:UserAgent` | any | **Forgeable** — client-supplied headers | → NOT SAFE |
| 12 | `aws:PrincipalAccount` (deprecated) | any | **Unreliable** — may not be present in all request contexts | → EXPECTED (not SAFE) |
| 13 | (absent) | — | **None** | → NOT SAFE |

## Output format (per finding)

```text
FINDING: <finding-id>
RESOURCE: <resource-arn>
RESOURCE_TYPE: <AWS::S3::Bucket | AWS::KMS::Key | AWS::IAM::Role | ...>
FINDING_TYPE: ExternalAccess | UnusedIAMRole | UnusedIAMUserAccessKey | ...
VERDICT: EXTERNAL_ACCESS | UNUSED_ACCESS | EXPECTED | SAFE
RISK: CRITICAL | HIGH | MODERATE | LOW
REASON: <1-2 sentences citing the finding type, principal, condition, and the classification rule that fired>
REMEDIATION: <specific action, or "None required" if expected/safe>
```

### Multi-finding triage example

```text
FINDING: external-access-kms-prod-key
RESOURCE: arn:aws:kms:us-east-1:123456789012:key/abc123
RESOURCE_TYPE: AWS::KMS::Key
FINDING_TYPE: ExternalAccess
VERDICT: EXTERNAL_ACCESS
RISK: CRITICAL
REASON: Principal "*" with no restrictive condition grants kms:Decrypt and kms:Encrypt on a KMS key. isPublic is true. KMS decrypt access is CRITICAL because it provides full data-access to anything encrypted with this key.
REMEDIATION: IMMEDIATE — restrict the KMS key policy to named internal principals only. If cross-account decrypt is required (e.g., shared data lake), add aws:SourceAccount or aws:SourceArn condition. Capture current policy: aws kms get-key-policy --key-id abc123 --policy-name default > /tmp/kms-backup.json before modifying.

FINDING: unused-role-legacy-etl
RESOURCE: arn:aws:iam::123456789012:role/legacy-etl-role
RESOURCE_TYPE: AWS::IAM::Role
FINDING_TYPE: UnusedIAMRole
VERDICT: UNUSED_ACCESS
RISK: MODERATE
REASON: Role unused for 95 days (last accessed 2024-10-01). Stale identity expands attack surface — the role has s3:GetObject and s3:PutObject on production buckets; if session tokens were cached before the role became inactive, they could still be valid.
REMEDIATION: Validate no workload depends on this role (check CloudTrail for any AssumeRole events in the last 30 days). If confirmed unused: detach policies, then delete the role. If still needed: scope down the policy and set a permissions boundary.
```

### Organization-scoped analyzer example (intra-org cross-account)

Full worked example (EXPECTED verdict with archive-rule remediation): [Worked examples](references/worked-examples.md).

## Anti-Patterns — NEVER

- NEVER classify a `Principal: "*"` finding with no condition (or a weak
  condition like `aws:Referer`) as SAFE. Without a cryptographic or
  network-scoped condition, the access is public or forgeable. `isPublic: true`
  in the finding confirms this — Access Analyzer has already evaluated the
  condition and determined the access is effectively public. Note: even
  `aws:SourceIp` does not save you here — IP conditions do not flip
  `isPublic` to false.

- NEVER treat `isPublic: false` as automatically safe. This is the most
  common triage error. `isPublic: false` ONLY means the principal is not
  `"*"` — it says nothing about whether the external account principal is
  trusted. An `isPublic: false` finding with an external account principal
  and no condition is still EXTERNAL_ACCESS because the external account
  could be compromised. The `isPublic` field answers "is this public?" —
  not "is this safe?" Always evaluate the condition and principal type
  independently of `isPublic`.

- NEVER classify a `Principal: "*"` finding with `aws:SourceArn` or
  `aws:SourceAccount` as EXTERNAL_ACCESS. These conditions are
  cryptographically enforced at the AWS service layer — the external principal
  cannot forge the source resource or account. Classifying these as
  EXTERNAL_ACCESS creates false-positive tickets and erodes trust in the
  triage process. The correct verdict is SAFE.

- NEVER mis-use organization-scoped analyzer flags. An account-scoped
  analyzer WILL flag intra-org cross-account access as external — this is
  correct behavior, not a false positive. If the principal is in a member
  account of the same org, the finding is EXPECTED (intra-org integration),
  not EXTERNAL_ACCESS. Conversely, do NOT assume an org-scoped analyzer
  finding is intra-org — an org analyzer only flags truly external
  principals. Check the principal's account against the org membership before
  applying the intra-org EXPECTED classification.

- NEVER classify an unused access key as EXPECTED. Unlike unused roles (which
  may be break-glass), unused access keys are static programmatic credentials
  with no MFA. They are credential-theft vectors. The only exception is an
  access key for a service user that is documented as intentionally rotated
  on a long cycle — even then, UNUSED_ACCESS is the safer verdict.

- NEVER recommend deleting a service-linked role (role name contains
  `aws-service-role` or the path includes `/service-role/`). Service-linked
  roles are managed by AWS services and will be recreated when the service
  needs them. Deleting them can break the service. The correct remediation is
  EXPECTED — "service-linked role, do not delete."

- NEVER archive a finding as "expected" without documenting the business
  justification. Archiving without documentation hides real risks and makes
  future audits impossible. Every archived finding should have an archive
  rule with a comment naming the integration, the owner, and the ticket
  reference.

- NEVER treat all AWS service principals as automatically safe. While most
  service principals are expected integrations, a service principal granting
  destructive actions on an unrelated resource is suspicious (e.g.,
  `lambda.amazonaws.com` granted `s3:DeleteObject` on a backup bucket — this
  is not a standard integration and should be investigated). Cross-check the
  service principal against the Expected service integrations table.

- NEVER ignore the finding's `analyzedAt` timestamp. If the finding was last
  analyzed more than 24 hours ago, the resource policy may have changed since
  the analysis. Always recommend re-running `aws accessanalyzer
  list-findings` before acting on a stale finding. A finding that appears
  CRITICAL may already be resolved if the policy was updated.

- NEVER recommend modifying a resource-based policy without first capturing
  the current policy. Resource policies are load-bearing for application
  access — removing a grant can break production workloads silently. Always
  capture a backup before any modification (pre-flight safety below).

- NEVER confuse an account-scoped analyzer with an organization-scoped
  analyzer. With an account analyzer, cross-account access within the same
  org IS flagged as external. With an org analyzer, it is NOT. The triage
  verdict depends on which analyzer generated the finding — the same finding
  can be EXPECTED (intra-org) or EXTERNAL_ACCESS (truly external) depending
  on the analyzer scope.

- NEVER treat `aws:SourceIp` with `0.0.0.0/0` as a restrictive condition.
  This CIDR covers the entire internet and provides zero restriction — it is
  functionally equivalent to no condition.

- NEVER treat `aws:PrincipalAccount` as equivalent to `aws:SourceAccount`.
  `aws:PrincipalAccount` is deprecated and may not be present in all request
  contexts. If a finding relies on it, classify as EXPECTED (not SAFE) and
  note the migration need.

## Pre-flight safety gate (run before ANY remediation CLI)

**HARD GATE: NEVER issue a destructive CLI command (`delete-*`, `put-*` on a
resource policy, `detach-*`, `deactivate-*`/`update-access-key --status
Inactive`, `delete-access-key`, or any command that modifies a resource-based
policy) without completing ALL pre-flight checks below first. If any check
fails or cannot be completed, STOP and report — do not proceed with the
remediation.**

- **Confirmation gate:** before executing any destructive CLI command, emit
  a confirmation prompt in the output: "CONFIRM: about to <command> on
  <resource>. This is potentially disruptive. Type 'yes' to proceed." Do not
  auto-execute destructive commands in a pipeline or script without this
  gate.

- Finding-freshness re-check command (list-findings ACTIVE filter): [Diagnostic commands](references/diagnostic-commands.md).

- **Capture current resource policy before modification.** Each resource type
  has a different command:
  Per-resource-type capture commands (S3, KMS, SQS, Secrets Manager, IAM role trust): [Diagnostic commands](references/diagnostic-commands.md).

Additive-vs-destructive change guidance (Deny is reversible; removed Allow loses intent): [Advanced patterns](references/advanced-patterns.md).

Public-write incident-response sequence (contain first, capture after — the one exception to capture-before-modify): [Advanced patterns](references/advanced-patterns.md).

Deactivate-before-delete procedure (update-access-key --status Inactive, 1-2 week observation): [Advanced patterns](references/advanced-patterns.md).

## Remediation guidance

### For EXTERNAL_ACCESS (public — Principal: "*", no condition)

Five-step playbook (containment → root-cause → conditional grant → CloudTrail audit → CreateGrant revocation): [Advanced patterns](references/advanced-patterns.md).

### For EXTERNAL_ACCESS (specific external account, no condition)

Four-step playbook (verify partner → archive rule → restrict → bound with condition): [Advanced patterns](references/advanced-patterns.md).

### For UNUSED_ACCESS (unused role)

Four-step playbook (CloudTrail validation → delete → scope-down → service-linked-role exception): [Advanced patterns](references/advanced-patterns.md).

### For UNUSED_ACCESS (unused access key)

Three-step playbook (deactivate → 90-day CloudTrail audit → delete): [Advanced patterns](references/advanced-patterns.md).

### For EXPECTED

Archive-rule creation, justification documentation, quarterly review: [Advanced patterns](references/advanced-patterns.md).

### For SAFE

Optional archive rule and audit-note guidance: [Advanced patterns](references/advanced-patterns.md).

## Archive-rule patterns

Archive rules suppress findings that match a filter, so they do not clutter
the active finding list. The proper pattern is:

Archive-rule JSON template, analyzer scoping (delegated administrator), and common patterns — log delivery, CI/CD roles, KMS data-lake consumers, SNS/SQS delivery: [Advanced patterns](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent features — unused-access GA, new resource types (S3 directory buckets, VPC endpoints, CloudWatch Logs), KMS/Secrets Manager coverage, org-level archive-rule management: [Advanced patterns](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — expert deltas, finding-type schemas, condition/principal detail, escalation rules, integrations table, remediation playbooks, archive-rule patterns, recent features
- [Worked examples](references/worked-examples.md) — zone-of-trust and organization-scoped analyzer worked examples
- [Error handling](references/error-handling.md) — malformed `condition` object handling
- [Diagnostic commands](references/diagnostic-commands.md) — pre-flight policy-capture commands per resource type

## Domain

AWS CloudOps / IAM Access Analyzer Security & Compliance.

## Related skills

Companion-skill usage detail: [Advanced patterns](references/advanced-patterns.md).

## AWS documentation

- **IAM Access Analyzer User Guide** — https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html
- **IAM Access Analyzer API Reference** — https://docs.aws.amazon.com/access-analyzer/latest/APIReference/
- **AWS CLI accessanalyzer command reference** — https://docs.aws.amazon.com/cli/latest/reference/accessanalyzer/
- **AWS IAM Security Best Practices** — https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- **Unused access analysis** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-unused-access.html
- **Blog: Identify unused IAM roles with IAM Access Analyzer** — https://aws.amazon.com/blogs/security/identify-unused-iam-roles-with-iam-access-analyzer-unused-access-analysis/
