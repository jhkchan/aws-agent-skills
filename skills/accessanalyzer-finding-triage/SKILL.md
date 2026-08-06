---
name: accessanalyzer-finding-triage
description: >-
  Triages IAM Access Analyzer findings (external access + unused access) into
  risk verdicts with remediation. Classifies each finding as real external
  exposure (EXTERNAL_ACCESS), stale credential or permission (UNUSED_ACCESS),
  expected cross-account or service integration (EXPECTED), or condition-bounded
  non-risk (SAFE). Evaluates the zone-of-trust model, principal type (public vs
  specific vs service), condition-key cryptographic strength, resource-type
  blast radius, and finding freshness. INVOKE DETERMINISTICALLY when the input
  contains an Access Analyzer finding JSON or finding reference — detection
  signal: findingType is ExternalAccess or starts with Unused, OR the input
  references isPublic, zone of trust, resource-based policy exposure, archive
  rule, or UnusedIAMRole/UnusedIAMUserAccessKey. Use when reviewing Access
  Analyzer findings, triaging external-access or unused-access findings,
  prioritizing remediation, or validating archive-rule suppression decisions.
version: 0.2.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf). No AWS
  CLI required for offline finding classification. Live-account triage uses
  aws accessanalyzer list-findings and aws accessanalyzer archive-rule
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - IAM Access Analyzer
  - external access
  - unused access
  - finding triage
  - zone of trust
  - isPublic
  - cross-account
  - resource-based policy
  - archive rule
  - UnusedIAMRole
  - unused access key
  - KMS key policy
  - S3 bucket policy
  - SQS queue policy
  - Secrets Manager
  - IAM role trust
  - condition strength
  - aws:SourceArn
  - aws:SourceAccount
  - service principal
tags: [iam, security, access-analyzer, finding-triage, external-access, unused-access, zone-of-trust]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  verdict_shape: "EXTERNAL_ACCESS | UNUSED_ACCESS | EXPECTED | SAFE"
  pattern: "Mindset → Quick Triage → Expert Deltas → Process → Matrices → Anti-Patterns → Pre-flight Gate → Remediation"
  when_to_use: >-
    Reviewing IAM Access Analyzer findings, triaging external-access or
    unused-access findings, prioritizing which findings to remediate first,
    validating whether a finding can be archived, or deciding if a
    cross-account resource-policy grant is an expected integration or a
    security risk.
---

# IAM Access Analyzer Finding Triage

**Structural pattern:** Mindset → Quick Triage → Expert Deltas → Process → Matrices → Anti-Patterns → Pre-flight Gate → Remediation. Read top-to-bottom; the Quick Triage section is sufficient for 80% of findings. Descend into Process and Matrices only for edge cases.

## Mindset

IAM Access Analyzer generates findings when a resource-based policy grants
access outside a defined **zone of trust**, or when an IAM identity (role,
user, access key, permission) is unused for a configurable analysis period.
The skill's job is not to restate what Access Analyzer already found — it is
to **triage** each finding into a risk verdict so the team knows what to fix
first, what to archive as expected, and what to dismiss as condition-bounded.

The critical insight: **not every Access Analyzer finding is a security
incident.** A KMS key policy granting `kms:Decrypt` to `config.amazonaws.com`
is a normal AWS service integration, not a data breach. An S3 bucket granting
`s3:PutObject` to another account with `aws:SourceArn` is cryptographically
bounded — the external account cannot misuse the access without the named
source resource. Conversely, a `Principal: "*"` grant with no condition is a
real public-exposure path regardless of how innocuous the resource seems.

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

1. **`isPublic: false` does NOT mean safe.** It only means the principal is not `"*"`. An external account principal with no condition is still EXTERNAL_ACCESS — the external account could be compromised.
2. **`Principal: "*"` + `aws:SourceArn` is SAFE**, not EXTERNAL_ACCESS. The source ARN is cryptographically validated at the AWS service layer — the external principal cannot forge it.
3. **Account vs Organization analyzer changes what is "external."** An account-scoped analyzer flags intra-org cross-account access; an org-scoped analyzer does not. The same finding can be EXPECTED (intra-org) or EXTERNAL_ACCESS (truly external) depending on analyzer scope.

## Expert knowledge deltas (non-obvious thresholds)

These are insights that a senior CloudOps engineer learns from production
incidents, not from the AWS documentation. Internalize them before triaging.

### Delta 1: Access Analyzer does NOT evaluate identity-based policies

Access Analyzer only analyzes **resource-based policies** (bucket policies,
key policies, trust policies, etc.). It does NOT check whether the external
principal's identity-based policy actually grants the permission. This means:

- A finding may be flagged even if **no identity in the external account can
  actually exercise the access** — the resource policy allows it, but the
  external account has no IAM entity with the matching permission.
- Conversely, if the resource policy is permissive (`Principal: "*"`) but the
  external principal has no identity-based grant, the finding is still
  EXTERNAL_ACCESS because the risk is the resource policy, not the current
  identity state. An identity-based policy could be added at any time.
- **Triage implication:** never dismiss a finding because "the external
  account probably doesn't have the permission." The resource policy is the
  risk surface — triage based on what it grants, not on assumed identity
  state.

### Delta 2: The `isPublic` computation algorithm

Access Analyzer sets `isPublic: true` only when the effective principal
resolves to `"*"` AND no condition narrows the principal to a finite set.
Key nuances the docs do not state explicitly:

- `aws:SourceIp` does NOT flip `isPublic` to `false` — IP addresses are not
  principal-scoping conditions. A `Principal: "*"` with `aws:SourceIp:
  10.0.0.0/8` will still show `isPublic: true`.
- `aws:SourceArn` and `aws:SourceAccount` DO flip `isPublic` to `false`
  because they scope to a specific resource or account.
- `aws:Referer` and `aws:UserAgent` do NOT flip `isPublic` to `false` — they
  are forgeable and not treated as principal-scoping.
- If `isPublic` is `true`, the condition (if any) is not principal-scoping.
  The finding is public exposure regardless of what the condition appears to
  restrict.

### Delta 3: `StringEquals` vs `StringLike` on `aws:SourceArn`

The condition operator determines how much trust the SourceArn provides:

- `StringEquals` with a concrete ARN (`arn:aws:cloudtrail:us-east-1:999999999999:trail/my-trail`)
  → **Strongest.** Exact match required; no wildcard expansion.
- `StringLike` with a wildcard pattern (`arn:aws:cloudtrail:*:999999999999:*`)
  → **Strong but broader.** Still scoped to account 999999999999, but any
  region and any trail name in that account qualifies. SAFE for most cases,
  but note that a compromised service in the source account could generate
  requests from any region/trail.
- `StringLike` with account-level wildcard (`arn:aws:cloudtrail:*:*:*`)
  → **Weak.** Effectively no account scoping. Treat as NOT SAFE unless
  additional conditions narrow the scope.

### Delta 4: The `kms:CreateGrant` escalation chain

A cross-account KMS key policy granting `kms:Decrypt` is CRITICAL on its own,
but the hidden escalation vector is `kms:CreateGrant`. If the external
principal can call `kms:CreateGrant`, they can delegate decrypt access to
**any other principal** in their account — including IAM users, roles, or
even lambda functions they control. This turns a direct decrypt path into a
delegation surface.

- **Triage rule:** if the action set includes `kms:CreateGrant` for a
  cross-account principal, the risk is always **CRITICAL** regardless of
  other actions. The delegation capability makes the blast radius
  unbounded within the external account.
- If only `kms:Decrypt`/`kms:Encrypt` are granted (no `CreateGrant`), the
  blast radius is limited to principals in the external account that the
  external account admin chooses to enable — still CRITICAL for KMS, but the
  delegation chain is shorter.

### Delta 5: Unused-access analysis period is configurable (not fixed at 90 days)

The default unused-access analysis period is 90 days, but it is configurable
to 30, 60, or 90 days via the analyzer configuration. Key implications:

- A role flagged as `UnusedIAMRole` with a 90-day period may have been used
  91 days ago — it is stale but not necessarily abandoned.
- A quarterly batch job (runs every 91+ days) will always show as unused in
  a 90-day window. Query CloudTrail for the actual last-accessed timestamp
  before recommending deletion.
- If the analysis period is set to 30 days, the noise volume increases
  significantly — more roles will appear "unused" that are simply
  infrequently used.

### Delta 6: The `analyzedAt` staleness threshold

Access Analyzer re-analyzes resources when the resource policy changes. But
the `analyzedAt` timestamp on a finding reflects when the analysis was last
performed, not when the policy last changed. Expert thresholds:

- **< 24 hours:** fresh — act on the finding as-is.
- **24 hours to 7 days:** stale — re-run `aws accessanalyzer list-findings`
  before acting. The policy may have changed since the analysis.
- **> 7 days:** very stale — the finding may already be resolved. Always
  re-run before any remediation action.

### Delta 7: `aws:PrincipalAccount` is deprecated — use `aws:SourceAccount`

Older policies may use `aws:PrincipalAccount` in conditions. This key is
deprecated and should not be treated as equivalent to `aws:SourceAccount`:
- `aws:SourceAccount` is evaluated at the service layer and cannot be forged.
- `aws:PrincipalAccount` may not be present in all request contexts and its
  semantics vary by service.
- If a finding's condition uses `aws:PrincipalAccount`, classify as
  EXPECTED (not SAFE) and note that the condition key should be migrated to
  `aws:SourceAccount`.

### Delta 8: Organization analyzer delegated administrator model

For organization-scoped analyzers, the analyzer is created in a **delegated
administrator account** (not the management account). Archive rules for
org-level findings must be created in the delegated administrator account.
This matters for triage:

- If you are triaging from the member account perspective, you cannot create
  archive rules for org-level findings — you must escalate to the delegated
  administrator.
- The REMEDIATION output should note which account can archive the finding
  based on the analyzer type.

## Zone of trust model (expert concept)

Access Analyzer defines a **zone of trust** based on the analyzer type. This
determines what counts as "external" — the same resource-policy grant can be
flagged or not flagged depending on which analyzer generated the finding:

| Analyzer type | Zone of trust | What is "external" |
|---|---|---|
| **Account** (`TYPE: ACCOUNT`) | The analyzer's AWS account only | Any principal in a different account — **including accounts in the same AWS Organization**. Cross-account access within the org IS flagged. |
| **Organization** (`TYPE: ORGANIZATION`) | The entire AWS Organization | Only principals outside the org. Cross-account access within the org is NOT flagged. |

**Triage implication:** when evaluating a finding, know which analyzer type
generated it. If an account-scoped analyzer flags access from another account
in the same org, that finding may be EXPECTED (intra-org integration) even
though the principal is technically "external" to the analyzer's zone. The
finding is valid per the analyzer's scope, but the risk is lower because the
principal is within the org's governance boundary.

**Example — organization-scoped analyzer expected case:**
An org-scoped analyzer flags an S3 bucket policy granting `s3:PutObject` to
`arn:aws:iam::999999999999:root` where account 999999999999 is a member of
the same org. With an org analyzer, this would NOT be flagged at all. With
an account analyzer, it IS flagged but should be classified as EXPECTED
(intra-org CI/CD deployment account) with an archive rule.

## Finding types

Access Analyzer generates two categories of findings. The skill handles both
but routes them through different classification paths:

### External access findings (`findingType: ExternalAccess`)

Generated when a **resource-based policy** grants access to a principal
outside the zone of trust. Resource-based policies include:

- S3 bucket policies, S3 access-point policies
- KMS key policies
- SQS queue policies, SNS topic policies
- Secrets Manager secret policies
- IAM role trust policies (the `AssumeRolePolicyDocument`)
- Lambda function policies, Lambda layer policies
- EFS file-system policies
- EventBridge event-bus policies
- AWS Backup vault policies
- OpenSearch domain policies
- Glue Data Catalog resource policies

Each external-access finding includes:
- `principal` — the external principal ARN, `"*"`, or a structured principal
  (`{"AWS": ...}`, `{"Service": ...}`, `{"Federated": ...}`)
- `isPublic` — boolean, pre-computed by Access Analyzer. `true` when the
  effective principal is `"*"` (or resolves to all principals) and no
  principal-scoping condition narrows it. See Delta 2 for the exact
  algorithm.
- `condition` — flattened map of condition key-value pairs from the policy
  statement that triggered the finding (not the full IAM condition block)
- `action` — list of IAM actions granted to the external principal
- `resourceType` — the AWS resource type (e.g., `AWS::S3::Bucket`)

### Unused access findings

Generated by **IAM Access Analyzer unused-access analysis** (a separate
analyzer configuration). Identifies IAM entities that have not been used
within the analysis period (default 90 days, configurable to 30/60/90):

| Finding type | What it means |
|---|---|
| `UnusedIAMRole` | Role not used by any service or principal in the analysis period |
| `UnusedIAMUserAccessKey` | An access key that has not been used for API calls |
| `UnusedIAMUserPassword` | Console password not used for login in the analysis period |
| `UnusedIAMPermission` | Specific IAM actions in a policy that have not been exercised |
| `UnusedServiceControlPolicy` | An SCP that does not affect any account in the org |

---

## Process — Classification logic (apply in order)

### Step 0: Validate input (AWS-specific field checks)

Verify the finding has the minimum fields required for triage. This is
not generic validation — each field gates a specific classification branch:

| Field | Required for | If missing |
|---|---|---|
| `findingType` | Routing (Step 1A vs 1B) | ERROR — cannot determine classification path |
| `status` | Step 1A.1 / 1B.1 (status check) | Assume ACTIVE (safer default) |
| `principal` | Step 1A.4 (principal classification) | For ExternalAccess: ERROR — cannot classify without principal |
| `condition` | Step 1A.2 (condition strength) | Treat as `{}` (absent condition) |
| `isPublic` | Step 1A.5 (severity escalation) | Infer from principal (`"*"` → `true`) |
| `action` / `actions` | Step 1A.5 (risk level) | If missing, assume worst-case for the resource type |
| `resourceType` | Step 1A.5 (severity matrix) | If missing, infer from resource ARN or flag as AMBIGUOUS |

**Malformed `condition` object handling:**
- `condition` is `null` or not a dict (e.g., a string or array) → treat as
  absent condition `{}`. Note in output: "condition field malformed —
  treated as absent."
- `condition` contains non-string values (e.g., numbers) → evaluate the key
  name for strength classification; note the type anomaly.
- `condition` contains nested operators (`"StringEquals": {...}`) → flatten
  to key-value pairs for strength evaluation; note the operator if it is
  `StringLike` (weaker than `StringEquals`, see Delta 3).

If `findingType` is missing or the finding JSON is unparseable, output:

```text
FINDING: <id or "unknown">
VERDICT: ERROR
REASON: Finding JSON is malformed or missing required fields — cannot triage.
REMEDIATION: Re-export the finding from aws accessanalyzer list-findings and verify the JSON structure.
```

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

Examine the `condition` field. Classify the condition strength using the
**Condition strength matrix** below. This is the primary differentiator
between EXTERNAL_ACCESS, SAFE, and EXPECTED:

**CRYPTOGRAPHIC conditions → SAFE (Step 1A.3):**
- `aws:SourceArn` with a **specific concrete ARN** using `StringEquals` (not
  a wildcard pattern) — the access is cryptographically bound to the named
  resource. AWS validates the source resource at the service layer; the
  external principal cannot forge it. This is the strongest possible
  restriction. See Delta 3 for operator semantics.
- `aws:SourceArn` with a wildcard pattern (e.g.,
  `arn:aws:cloudtrail:*:999999999999:*`) using `StringLike` — still STRONG
  but scoped to the account. Classify as SAFE with a note that wildcard ARN
  patterns are broader than concrete ARNs (a compromised service in the
  source account could generate requests from any region).

**ACCOUNT-SCOPED conditions → SAFE (Step 1A.3):**
- `aws:SourceAccount` with a specific account ID — the request must originate
  from the named account. Cannot be forged. If the account is a known partner
  or member of the same org, this is SAFE. If the account is unknown, this is
  still technically bounded but should be flagged for identity verification —
  downgrade to EXPECTED with a note.
- **Deprecated:** `aws:PrincipalAccount` (see Delta 7) — classify as EXPECTED,
  not SAFE, and note the condition key should be migrated.

**ORGANIZATION-SCOPED conditions → SAFE:**
- `aws:PrincipalOrgID` with the org ID — restricts to principals within the
  named AWS Organization. SAFE if the org is your own; AMBIGUOUS if the org is
  a third-party org.

**NETWORK-SCOPED conditions → SAFE for private, AMBIGUOUS for public:**
- `aws:SourceVpce` (VPC Endpoint ID) — request must traverse the named
  endpoint. Cannot be forged by external callers.
- `aws:SourceVpc` (VPC ID) — request must originate in the named VPC.
- If the VPC/VPCe has internet gateway routes, the network scoping is weaker
  (an attacker inside the VPC could relay). Still SAFE for most practical
  purposes, but note the assumption.
- **`aws:SourceIp` does NOT flip `isPublic` to false** (see Delta 2). IP
  conditions are not principal-scoping. Evaluate separately: RFC1918 CIDR
  without IGW route → SAFE; `0.0.0.0/0` → NOT SAFE (equivalent to no
  condition); public CIDR → AMBIGUOUS.

**SERVICE-COUPLED conditions → SAFE:**
- `kms:ViaService` — KMS access only through a named AWS service (e.g.,
  `kms:ViaService: "s3.us-east-1.amazonaws.com"`). The caller cannot decrypt
  directly; they must go through the named service. Note: this is weaker than
  `aws:SourceArn` because the caller still controls which service they route
  through, but the named service enforces its own access controls.

**WEAK / FORGEABLE conditions → NOT SAFE (treat as no condition):**
- `aws:Referer` — client-supplied HTTP header, trivially forgeable by any HTTP
  client. Provides zero access control.
- `aws:UserAgent` — same; forgeable client-side.
- Any condition wrapped only in `IfExists` — weakens the assertion to
  "evaluate if present, ignore if absent." Treat per the underlying key but
  flag the `IfExists` semantics.
- `aws:SourceArn` with `StringLike` and account-level wildcard
  (`arn:aws:s3:*:*:*`) — effectively no account scoping.

**ABSENT condition → NOT SAFE:**
- If `condition` is `{}` or missing, the access is unconditional. Proceed to
  Step 1A.4.

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
- Check the **Expected service integrations** table below. If the service
  principal matches a known integration pattern for the resource type, output
  EXPECTED.
- Service principals in role trust policies (e.g.,
  `lambda.amazonaws.com`, `ecs-tasks.amazonaws.com`, `ec2.amazonaws.com`)
  are the standard pattern for service execution roles → EXPECTED.
- Service principals in KMS/S3 resource policies (e.g.,
  `config.amazonaws.com`, `cloudtrail.amazonaws.com`, `logging.amazonaws.com`)
  are standard service-to-resource integrations → EXPECTED.
- **Exception:** if the service principal grants broad destructive actions
  (e.g., `s3:DeleteObject` to a generic service principal, or
  `iam:PutRolePolicy` to an unexpected service), flag as EXTERNAL_ACCESS with
  a note that the service principal pattern is unusual.

**Federated principal** (`{"Federated": "arn:aws:iam::ACCOUNT:saml-provider/xxx"}` or `{"Federated": "arn:aws:iam::ACCOUNT:oidc-provider/xxx"}`):
- A federation integration (Okta, Azure AD, GitHub OIDC). If the identity
  provider is in the same account, this is an internal federation path →
  EXPECTED. If the IdP is in an external account → EXTERNAL_ACCESS (unusual
  and high-risk: external IdP control over role assumption).

**Specific external account principal** (`arn:aws:iam::EXTERNAL_ACCOUNT:root` or specific role/user):
- No condition, external account, resource policy grants access →
  EXTERNAL_ACCESS. The risk level depends on the resource type and actions
  (Step 1A.5).
- **Exception:** if the input includes context that the external account is a
  known CI/CD deployment account, monitoring account, or documented SaaS
  partner, classify as EXPECTED with a note to create an archive rule.

**Public principal** (`"*"`, `{"AWS": "*"}`):
- No restrictive condition + public principal → EXTERNAL_ACCESS. The risk
  level depends on the resource type and actions (Step 1A.5). If `isPublic`
  is `true`, the finding is confirmed public by Access Analyzer.

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
- If `isPublic` is `true` AND the resource type is KMS, Secrets Manager, or
  S3 with write actions, this is **incident-response priority** — flag the
  REMEDIATION as "IMMEDIATE."
- For specific external account principals (not public), downgrade by one
  level from the matrix (CRITICAL → HIGH, HIGH → MODERATE) because the
  exposure is to one account, not the entire internet — unless the actions
  are admin/trust (stays CRITICAL).
- **KMS escalation chain (Delta 4):** if the action set includes
  `kms:CreateGrant` for a cross-account principal, risk is always
  **CRITICAL** regardless of other actions — the delegation capability
  makes the blast radius unbounded within the external account.

#### Step 1A.6: Expected service integrations reference

If the principal is a service principal AND the resource type + actions match
a row below, classify as **EXPECTED**:

| Service principal | Resource type | Expected actions | Integration |
|---|---|---|---|
| `cloudtrail.amazonaws.com` | S3 Bucket | `s3:GetBucketAcl`, `s3:PutObject` | CloudTrail log delivery |
| `logging.amazonaws.com` | S3 Bucket | `s3:PutObject` | S3 server access log delivery |
| `config.amazonaws.com` | S3 Bucket, KMS Key | `s3:GetBucketAcl`, `s3:PutObject`, `kms:Decrypt`, `kms:GenerateDataKey` | AWS Config configuration recording |
| `config-multiaccountsetup.amazonaws.com` | IAM Role | `sts:AssumeRole` | Config multi-account aggregator |
| `lambda.amazonaws.com` | IAM Role | `sts:AssumeRole` | Lambda execution role |
| `ecs-tasks.amazonaws.com` | IAM Role | `sts:AssumeRole` | ECS task execution role |
| `ec2.amazonaws.com` | IAM Role | `sts:AssumeRole` | EC2 instance profile |
| `ssm.amazonaws.com` | IAM Role | `sts:AssumeRole` | Systems Manager managed instance |
| `backup.amazonaws.com` | KMS Key, Backup Vault | `kms:Decrypt`, `kms:Encrypt`, `backup:*` | AWS Backup service |
| `elasticloadbalancing.amazonaws.com` | S3 Bucket | `s3:PutObject` | ALB/NLB access log delivery |
| `sns.amazonaws.com` | S3 Bucket | `s3:PutObject` | S3 event notification delivery |
| `sqs.amazonaws.com` | S3 Bucket | `s3:PutObject` | S3 event notification delivery |
| `events.amazonaws.com` | SNS Topic, SQS Queue, EventBridge | `sns:Publish`, `sqs:SendMessage`, `events:PutEvents` | EventBridge rule target delivery |
| `delivery.logs.amazonaws.com` | S3 Bucket | `s3:PutObject` | CloudWatch Logs delivery to S3 |
| `athena.amazonaws.com` | S3 Bucket | `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` | Athena query results read/write |
| `states.amazonaws.com` | Lambda, SNS, SQS | `lambda:InvokeFunction`, `sns:Publish`, `sqs:SendMessage` | Step Functions service integration |
| `guardduty.amazonaws.com` | S3 Bucket, KMS Key | `s3:PutObject`, `kms:GenerateDataKey` | GuardDuty finding export |
| `securityhub.amazonaws.com` | S3 Bucket | `s3:PutObject` | Security Hub finding export |
| `firehose.amazonaws.com` | S3 Bucket | `s3:PutObject` | Kinesis Firehose delivery |
| `vpn.amazonaws.com` | S3 Bucket | `s3:GetObject` | Client VPN endpoint configuration |

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
- An unused access key is a **credential-theft vector** — it provides
  programmatic API access with no MFA requirement. If exfiltrated (e.g.,
  from a CI config, committed `.aws/credentials`, or a compromised
  developer machine), the attacker has silent API access.
- Risk is always **HIGH** for unused access keys, regardless of the user's
  attached policies. Even a read-only user's unused key is HIGH because the
  key itself is the risk (it's a static credential sitting dormant).
- If the user has admin-level policies attached, escalate to **CRITICAL**.

**UnusedIAMUserPassword → UNUSED_ACCESS / MODERATE:**
- An unused console password is lower risk than an access key because console
  access typically requires MFA (if configured). But if MFA is not enforced,
  the password alone is a console access path.
- Risk is **MODERATE**. Escalate to **HIGH** if MFA is not enabled for the
  user.

**UnusedIAMRole → UNUSED_ACCESS / MODERATE (default):**
- A role unused for 90+ days is a **credential-hygiene risk** — stale
  identities expand the attack surface. If the role's credentials (temporary
  session tokens) were obtained and cached before the role became unused, they
  could still be valid.
- Default risk is **MODERATE**. Adjust based on the role's attached policies:
  - Role with `AdministratorAccess` or wildcard actions → **HIGH**
  - Role with read-only or scoped permissions → **MODERATE**
  - Role with write access to production resources → **HIGH**

**UnusedIAMPermission → UNUSED_ACCESS / LOW:**
- Individual unused actions within a policy are a **scoping opportunity**, not
  an active vulnerability. The actions are not exercised, so they can be
  removed without impact (after validation).
- Risk is **LOW**. The remediation is to generate a scoped policy from
  CloudTrail activity (same workflow as `iam-least-privilege-advisor`).

**UnusedServiceControlPolicy → UNUSED_ACCESS / LOW:**
- An SCP that does not affect any account is a **governance cleanup** item.
- Risk is **LOW**. The SCP may be intentionally broad (deny-by-default) or
  may be a leftover from a reorganization.

#### Step 1B.3: Expected-unused patterns

Certain unused entities are **intentionally unused** and should be classified
as EXPECTED:

- **Service-linked roles** (role name contains `/service-role/` or the path
  includes `aws-service-role`) — these are managed by AWS services and should
  NOT be deleted even if unused. They will be recreated when the service
  needs them. → EXPECTED with note "service-linked role — do not delete."

- **Break-glass / emergency-access roles** — if the input includes context
  that the role is a documented emergency-access role (name contains
  `break-glass`, `emergency`, `incident-response`, `dr-`), classify as
  EXPECTED with note "break-glass role — expected to be unused; verify access
  logging is enabled."

- **Cross-account audit roles** — roles assumed by a security or audit tool
  account for periodic compliance scans. These may be used infrequently
  (monthly/quarterly) and may appear unused in a 90-day window. → EXPECTED
  with note to extend the analysis period or add the role to an exclusion
  list.

- **AWS-managed job-function roles** (e.g., `AWSBatchServiceRole`,
  `AWSServiceRoleFor*`) — these are service-managed and should not be
  modified. → EXPECTED.

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

```text
FINDING: s3-cross-account-org-member
RESOURCE: arn:aws:s3:::shared-data-lake
RESOURCE_TYPE: AWS::S3::Bucket
FINDING_TYPE: ExternalAccess
VERDICT: EXPECTED
RISK: LOW
REASON: Principal arn:aws:iam::999999999999:root (account 999999999999) is a member of the same AWS Organization as the resource owner account 123456789012. The account-scoped analyzer correctly flagged this as external to its zone of trust, but the principal is within the org governance boundary. The CI/CD deployment account 999999999999 is a documented data-lake consumer.
REMEDIATION: Create an archive rule on the account analyzer: filter on principal=arn:aws:iam::999999999999:root + resourceType=AWS::S3::Bucket. Document the integration owner and ticket reference. Alternatively, upgrade to an organization-scoped analyzer to eliminate these intra-org findings automatically.
```

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

- **Verify finding freshness:** re-run `aws accessanalyzer list-findings
  --analyzer-arn <arn> --filter '{"status":{"eq":["ACTIVE"]}}'` to confirm
  the finding is still ACTIVE before acting. Stale findings waste effort.

- **Capture current resource policy before modification.** Each resource type
  has a different command:
  - S3: `aws s3api get-bucket-policy --bucket <name> --output json >
    /tmp/<name>-policy-backup-$(date +%s).json`
  - KMS: `aws kms get-key-policy --key-id <key-id> --policy-name default >
    /tmp/<key-id>-policy-backup-$(date +%s).json`
  - SQS: `aws sqs get-queue-attributes --queue-url <url>
    --attribute-names Policy --output json >
    /tmp/<queue>-policy-backup-$(date +%s).json`
  - Secrets Manager: `aws secretsmanager get-resource-policy
    --secret-id <id> > /tmp/<secret>-policy-backup-$(date +%s).json`
  - IAM role trust: `aws iam get-role --role-name <name> --query
    'Role.AssumeRolePolicyDocument' --output json >
    /tmp/<role>-trust-backup-$(date +%s).json`

- **Prefer additive changes** (adding a Deny statement, adding a condition)
  over destructive changes (removing a statement, deleting a policy). A Deny
  is reversible by removing the Deny; a removed Allow may lose the intent
  that originally created the grant.

- **For public-write findings (EXTERNAL_ACCESS / CRITICAL on S3, EFS, Backup
  Vault), treat as incident response.** The fastest containment is usually a
  broad Deny statement (`"Effect": "Deny", "Principal": "*", "Action": "*",
  "Resource": "<arn>"`) or removing the public statement — do this BEFORE
  full forensic capture, because every second of public-write exposure is
  data destruction risk. Capture state AFTER containing. This is the ONE
  exception to the "capture before modify" rule — for active public-write
  exposure, containment is higher priority than backup.

- **For unused access keys, deactivate (not delete) first.** `aws iam
  update-access-key --access-key-id <id> --status Inactive` is reversible.
  Delete only after confirming no workload breaks (1-2 week observation
  period via CloudTrail).

## Remediation guidance

### For EXTERNAL_ACCESS (public — Principal: "*", no condition)

1. **Immediate containment:** add a Deny-all statement or restrict the
   principal to specific internal ARNs. For S3, enable Block Public Access
   (BPA) at bucket level — this is the fastest containment.
2. **Root-cause the policy:** identify who created the public grant and why.
   Often it was a debugging shortcut (`Principal: "*"` to test access) that
   was never removed.
3. **If cross-account access is legitimately needed:** replace `Principal:
   "*"` with the specific external account ARN and add `aws:SourceAccount`
   or `aws:SourceArn` condition.
4. **Audit CloudTrail** for the exposure window: check for unauthorized
   `GetObject`, `PutObject`, `Decrypt`, or `AssumeRole` events from
   principals outside your account during the period the policy was public.
5. **Check for `kms:CreateGrant` in the action set** (Delta 4) — if present,
   the external account may have created delegation grants. Audit
   ` kms:CreateGrant` events and revoke any unauthorized grants:
   `aws kms list-grants --key-id <key-id>`.

### For EXTERNAL_ACCESS (specific external account, no condition)

1. **Verify the external account is known.** Check with the application owner
   whether the external account is a partner, CI/CD pipeline, or monitoring
   tool.
2. If known → classify as EXPECTED and create an archive rule to suppress
   future instances: filter on the principal ARN + resource type + actions.
3. If unknown → restrict immediately. Remove the external account from the
   resource policy and monitor CloudTrail for any legitimate access that
   breaks.
4. **If the access must remain,** add a condition (`aws:SourceAccount` or
   `aws:SourceArn`) to bound it cryptographically, then downgrade to SAFE.

### For UNUSED_ACCESS (unused role)

1. **Validate non-use:** query CloudTrail for any `AssumeRole` events on the
   role ARN in the last 30-90 days. Access Analyzer's 90-day window may miss
   quarterly batch jobs — extend the query if needed.
2. **If confirmed unused:** detach all managed policies, delete inline
   policies, then delete the role. Capture the role configuration first:
   `aws iam get-role --role-name <name> > /tmp/<name>-backup.json`.
3. **If still needed but over-permissioned:** generate a scoped policy from
   CloudTrail activity (same workflow as `iam-least-privilege-advisor`) and
   replace the existing policy.
4. **For service-linked roles:** do NOT delete. Classify as EXPECTED.

### For UNUSED_ACCESS (unused access key)

1. **Deactivate immediately** (not delete): `aws iam update-access-key
   --access-key-id <id> --status Inactive --user-name <name>`. This is
   reversible and stops the credential-theft vector.
2. **Audit CloudTrail** for any API calls using this key in the last 90 days.
   If the key was used by an unknown source, treat as a potential compromise
   — rotate all credentials for the user and investigate.
3. **After 1-2 weeks of no breakage,** delete the key: `aws iam
   delete-access-key --access-key-id <id> --user-name <name>`.

### For EXPECTED

1. **Create an archive rule** to suppress future instances of the same
   pattern. The archive rule should filter on the principal, resource type,
   and condition that identify the expected integration.
2. **Document the justification:** integration name, owner, ticket reference.
3. **Periodically review** archived findings (quarterly) to verify the
   integration is still active and the external principal has not been
   compromised.

### For SAFE

1. No remediation required. The condition bounds the access.
2. Optionally create an archive rule to suppress future instances of
   condition-bounded findings on the same resource type.
3. Note the condition in the finding's archive comment for future auditors.

## Archive-rule patterns

Archive rules suppress findings that match a filter, so they do not clutter
the active finding list. The proper pattern is:

```json
{
  "filter": {
    "resourceType": {"eq": ["AWS::S3::Bucket"]},
    "principal": {"contains": ["cloudtrail.amazonaws.com"]},
    "action": {"contains": ["s3:PutObject"]}
  }
}
```

Archive rules are analyzer-scoped — they apply to one analyzer. For
organization analyzers, create archive rules at the delegated administrator
account level (see Delta 8). For account analyzers, create archive rules
in the account that owns the analyzer.

**Common archive-rule patterns:**
- AWS service log delivery (CloudTrail, Config, ELB, S3 access logs)
- Cross-account CI/CD deployment roles (filter on the CI/CD account principal
  + `sts:AssumeRole`)
- KMS key decrypt for known data-lake consumer accounts (filter on
  `kms:Decrypt` + `aws:SourceAccount`)
- SNS/SQS cross-account event delivery (filter on the monitoring account
  principal)

## Recent AWS features (2024-2026)

- **Unused-access analysis GA (2024):** UnusedIAMRole, UnusedIAMUserAccessKey, UnusedIAMPermission, and UnusedServiceControlPolicy finding types are now GA for account and organization analyzers. The skill already covers these, but auditors should expect a higher volume of unused-access findings now that the feature is enabled by default on new analyzers.
- **New supported resource types:** Access Analyzer now evaluates resource-based policies for S3 directory buckets (`AWS::S3Express::DirectoryBucket`), VPC endpoints (`AWS::EC2::VPCE`), and CloudWatch Logs resource policies. Findings from these new types flow through the same triage logic — ensure archive rules account for them.
- **External-access analyzer for KMS and Secrets Manager:** expanded coverage means more granular findings for KMS key grants and Secrets Manager resource policies. The Delta 4 (kms:CreateGrant escalation) logic applies to these new finding shapes.
- **Organization-level analyzer enhancements:** delegated administrator can now manage archive rules across the org centrally, and unused-access findings include `UnusedServiceControlPolicy` which affects SCP audit posture.

## Domain

AWS CloudOps / IAM Access Analyzer Security & Compliance.

## Related skills

- **`iam-least-privilege-advisor`** — classifies identity-based IAM policies
  for wildcard and escalation risk. Use after remediating an unused-access
  finding to scope down the replacement policy.
- **`s3-public-access-auditor`** — audits S3 bucket configurations for public
  access. Complements this skill's S3 external-access finding triage with
  BPA/ACL-level analysis.

## AWS documentation

- **IAM Access Analyzer User Guide** — https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html
- **IAM Access Analyzer API Reference** — https://docs.aws.amazon.com/access-analyzer/latest/APIReference/
- **AWS CLI accessanalyzer command reference** — https://docs.aws.amazon.com/cli/latest/reference/accessanalyzer/
- **AWS IAM Security Best Practices** — https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- **Unused access analysis** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-unused-access.html
- **Blog: Identify unused IAM roles with IAM Access Analyzer** — https://aws.amazon.com/blogs/security/identify-unused-iam-roles-with-iam-access-analyzer-unused-access-analysis/
