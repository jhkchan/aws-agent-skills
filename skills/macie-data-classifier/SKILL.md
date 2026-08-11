---
name: macie-data-classifier
description: >-
  Audits Amazon Macie data discovery and classification posture across
  S3 estates — sensitive data discovery jobs (PII, financial,
  credentials via managed data identifiers), custom data identifiers
  (regex-based), automated sensitive data discovery (ASDD) vs targeted
  one-time/scheduled jobs, job scoping with inclusion/exclusion
  criteria, finding types and severities, suppression rules, multi-
  account topology (Macie administrator/member via Organizations),
  findings publication to Security Hub and CloudWatch Events, data
  sampling depth vs full-scan trade-off, and custom identifier regex
  cost modeling. Emits a CLASSIFIED, PARTIALLY_CLASSIFIED, or
  UNCLASSIFIED verdict with a gap-cited checklist. Use when assessing
  Macie coverage, auditing PII detection posture, validating
  classification job scoping, reviewing suppression rule hygiene, or
  verifying Security Hub integration. Triggers: audit macie, macie
  data classification, pii discovery coverage, macie job scoping,
  sensitive data s3 scan, custom data identifier, macie security hub.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). For live audit: AWS CLI v2 with macie2, s3, securityhub, sts,
  organizations, and events access. Works with Terraform
  aws_macie2_account / aws_macie2_classification_job /
  aws_macie2_custom_data_identifier / aws_macie2_findings_filter data
  sources and CloudFormation AWS::Macie::* templates for plan validation.
keywords:
  - aws
  - macie
  - data classification
  - cloudops
  - audit
  - pii
  - sensitive data
  - managed data identifiers
  - custom data identifiers
  - classification job
  - job scoping
  - automated discovery
  - suppression rules
  - findings filter
  - security hub
  - cloudwatch events
  - eventbridge
  - multi-account
  - delegated admin
  - data sampling
  - s3 scanning
tags:
  - aws
  - macie
  - security
  - cloudops
  - audit
  - data-classification
  - pii-detection
  - sensitive-data
  - security-hub
  - multi-account
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: audit
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "CLASSIFIED | PARTIALLY_CLASSIFIED | UNCLASSIFIED"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - macie
    - security
    - cloudops
    - audit
    - data-classification
    - pii-detection
    - sensitive-data
    - security-hub
    - multi-account
  dependencies:
    - aws-orchestrator
  keywords:
    - audit macie
    - macie data classification
    - pii discovery coverage
    - macie job scoping
    - sensitive data s3 scan
    - custom data identifier
    - macie security hub
    - macie multi-account
    - macie suppression rules
    - automated sensitive data discovery
  when_to_use: >-
    Invoke when the user wants to audit or assess Amazon Macie data
    discovery and classification coverage — verifying that classification
    jobs cover all sensitive S3 buckets, that automated discovery is
    enabled, that custom data identifiers exist for organization-specific
    sensitive data, that suppression rules are intentional and not masking
    real findings, that findings route to Security Hub and CloudWatch
    Events, or that the Macie administrator/member multi-account topology
    is correctly configured. Do NOT invoke for operating Macie jobs
    (use macie-data-discovery-operator), provisioning Macie resources, or
    auditing non-Macie security services.
---

# Macie Data Classifier

An AWS CloudOps agent skill that audits Amazon Macie data discovery and
classification posture. The skill walks the operator through Macie
enablement, automated discovery, classification job scoping, managed vs
custom data identifiers, finding types, suppression rule hygiene, multi-
account delegation, Security Hub and EventBridge integration, and
sampling depth — then emits a CLASSIFIED, PARTIALLY_CLASSIFIED, or
UNCLASSIFIED verdict with a gap-cited checklist and verification commands.

## Activation keywords

audit Macie, Macie data classification review, PII discovery coverage,
Macie job scoping audit, sensitive data S3 scan, custom data identifier
review, Macie Security Hub integration, Macie multi-account, Macie
suppression rules, automated sensitive data discovery.

## STRICT output contract

When this skill is invoked with a Macie classification audit request,
the agent MUST respond with the classification checklist defined in the
"Output format" section using the literal all-caps labels
`MACIE_CLASSIFICATION:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
audit pipelines rely on; deviating from the literal labels breaks
automation silently.

If any coverage gap is material (Macie disabled, no ASDD, no jobs
covering sensitive buckets, no custom identifiers, Security Hub export
off), the verdict is `PARTIALLY_CLASSIFIED` with a specific gap citation
marked `[✗]`, and `CLASSIFIED` MUST NOT also appear. If Macie is disabled
entirely or no jobs exist, the verdict is `UNCLASSIFIED`.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before auditing |
| Step 1 — Macie enablement and status | Core enablement check |
| Step 2 — Automated sensitive data discovery (ASDD) | ASDD coverage |
| Step 3 — Classification jobs and scoping | Job-level scanning |
| Step 4 — Managed data identifiers | Built-in detector coverage |
| Step 5 — Custom data identifiers | Org-specific detection |
| Step 6 — Finding types and severities | Finding classification |
| Step 7 — Suppression rules (findings filters) | Noise reduction hygiene |
| Step 8 — Multi-account Macie topology | Org-level delegation |
| Step 9 — Security Hub and CloudWatch Events | Findings routing |
| Step 10 — Sampling depth vs full scan | Coverage vs cost |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/job-scoping-and-identifiers.md | Scoping + identifier detail |
| references/multi-account-and-findings-routing.md | Delegation + routing detail |

## Mindset

**One-line takeaway:** Amazon Macie classifies S3 objects for sensitive
data using managed data identifiers (PII, financial, credentials) and
custom regex-based identifiers. Coverage is determined by three axes:
(1) whether Macie is enabled and ASDD is on, (2) whether classification
jobs scope the right buckets with inclusion/exclusion criteria, and (3)
whether custom identifiers exist for organization-specific data types.

Three misconceptions dominate Macie audit misassessment:

- **"Macie is enabled, so all S3 data is classified."** It is NOT.
  Macie enablement is the floor. Without ASDD enabled and classification
  jobs scoped to the right buckets, Macie scans nothing. The #1 audit
  gap is assuming enablement equals coverage.

- **"Suppression rules are always intentional."** They are NOT. A filter
  with `action: SUPPRESS` on broad criteria (all High severity) hides
  real findings from Security Hub and CloudWatch Events. A suppression
  rule that masks HIGH severity findings without a documented exception
  is a red flag.

- **"Custom data identifiers are free."** They are NOT. Regex with
  catastrophic backtracking (nested quantifiers) can cause job timeouts.
  Overly broad regex (`\d{1,19}`) produces false-positive floods. Regex
  must be scoped and benchmarked.

## Configuration dependency graph (novel heuristic)

Macie classification configurations are NOT independent. Macie must be
enabled before jobs can be created. ASDD must be enabled for continuous
bucket monitoring. Custom identifiers must exist before jobs reference
them. Security Hub integration must be explicitly enabled.

| Configuration | Hard dependencies | Silent failure / false sense | Enables downstream |
|---|---|---|---|
| Macie enabled | None — foundational | Enabled but no jobs = looks healthy but scans nothing | ASDD, jobs, findings |
| ASDD | Macie enabled | Samples objects only — may MISS data beyond sample window | continuous discovery |
| Classification jobs | Macie enabled; S3 scope defined | Job scoped to `s3://*` with no excludes = expensive/noisy; too narrow = misses data | deterministic deep-scan findings |
| Managed identifiers | None — built-in | Always available, but only covers standard PII/financial/credential types | standard finding types |
| Custom identifiers | Macie enabled; regex validated | Catastrophic backtracking = timeouts; broad regex = false-positive flood | org-specific finding types |
| Suppression rules | Macie enabled; findings exist | `SUPPRESS` action masks findings from SH + CWE silently | noise reduction (or masking) |
| Security Hub integration | Macie + SH enabled in same Region | If export OFF, findings siloed in Macie console — SOC sees nothing | centralized aggregation |
| CloudWatch Events | Macie enabled; EventBridge rule configured | Without rule, no automated response fires | automated remediation |
| Multi-account delegation | Admin account designated; members associated | Members PAUSED/disassociated silently unmonitored | org-wide classification |

**The ASDD-vs-job-scope row is the one a baseline model misses.**
Enablement + ASDD gives the appearance of coverage, but ASDD only
samples objects. Classification jobs provide deterministic deep scans,
but only for scoped buckets. The gap between "buckets Macie knows about"
and "buckets with deep-scan jobs" is the #1 coverage blind spot.

## Expert heuristic: job scoping — inclusion vs exclusion patterns

A baseline model says "Macie scans S3." The correct heuristic recognizes
that classification jobs have a scoping block with `includes` and
`excludes` criteria — and the WRONG scope produces either missed
sensitive data or runaway scan costs.

```text
Scoping decision tree:
  ├── Sensitive buckets known → targeted includes (deterministic, cost-bounded)
  │     Con: misses new buckets not in the include list
  ├── Broad scan with excludes → includes s3://*, excludes known non-sensitive
  │     Pro: catches new buckets; Con: scans EVERYTHING → high cost, slow
  └── Tag-based scoping → include by DataClass=sensitive tag
        Pro: scalable; Con: requires consistent tagging
```

**Key implication:** the most common audit gap is a job scoped too
broadly that runs once, incurs high cost, gets disabled, and never
re-runs — leaving zero ongoing coverage.

## Expert heuristic: sampling depth vs full-scan trade-off

ASDD samples objects — it does NOT deep-scan every object. The trade-off:

```text
  ASDD (automated): samples ~first N objects per bucket. Low cost, continuous.
    Con: may MISS sensitive data in rarely-accessed objects.

  One-time job: scans ALL objects in scope. Deterministic. One-time snapshot.

  Scheduled job: runs on cron. Periodic deep coverage + trend tracking.
    Con: ongoing S3 GET cost for large estates.

Decision matrix:
  High sensitivity (PII, finance)  → Scheduled job, full-scan, REQUIRED
  Medium (app data)                → Scheduled job recommended
  Low (logs, temp)                 → ASDD baseline sufficient
```

An audit that checks "Macie enabled + ASDD on" and declares CLASSIFIED is
wrong for high-sensitivity estates. High-sensitivity buckets need
scheduled classification jobs with full-scan depth, not just ASDD.

## Expert heuristic: custom identifier regex cost

```text
Regex cost factors:
  ✗ Catastrophic backtracking: (a+)+b, (.*).*meta → exponential
  ✗ Unbounded quantifiers: \d{1,19} → matches everything numeric
  ✗ No word boundaries: KEY-[A-Z0-9]{20} → matches inside longer strings
  ✓ Bounded + word boundaries: \bEMP-\d{6}\b → scoped
  ✓ Ignore-words list: ["example","test"] → reduces false positives

Score each regex:
  +1 word boundaries, +1 bounded quantifiers, +1 specific char classes,
  +1 format delimiters, +1 ignore-words
  -2 nested quantifiers, -1 wildcard prefix, -1 no boundaries
  Score 4-5: healthy  |  Score 2-3: review  |  Score 0-1: high risk
```

## Prerequisites (verify before auditing)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Macie enabled | Cannot audit what is not enabled | `aws macie2 get-macie-session` |
| Macie admin account identified | Multi-account audit needs admin context | `aws organizations list-delegated-administrators --service-principal macie.amazonaws.com` |
| Region(s) identified | Macie is regional; findings are regional | Confirm target Regions |
| IAM permission for macie2 APIs | Audit requires read access | Verify `macie2:List*`, `macie2:Get*` |
| S3 bucket inventory | Compare Macie coverage vs actual buckets | `aws s3api list-buckets --query 'Buckets[*].Name'` |
| Security Hub enabled (if checking integration) | SH export requires SH enabled | `aws securityhub describe-hub` |

If Macie is not enabled, output `VERDICT: UNCLASSIFIED` and cite the gap.

## Step 1 — Macie enablement and status

| Status | Meaning | Audit implication |
|---|---|---|
| ENABLED | Macie is active | Proceed to coverage audit |
| PAUSED | Enabled but temporarily paused | Coverage gap — findings may be stale |
| Not enabled | No Macie session | UNCLASSIFIED |

```bash
aws macie2 get-macie-session --region us-east-1 \
  --query '{Status:status,Frequency:findingPublishingFrequency}'
```

## Step 2 — Automated sensitive data discovery (ASDD)

```bash
aws macie2 get-automated-discovery-configuration --region us-east-1 \
  --query '{Status:status,AutoEnable:autoEnableOrganizationMembers}'
```

| Check | Gap if missing |
|---|---|
| ASDD enabled (`status: ENABLED`) | No automatic bucket discovery — new buckets unmonitored |
| Auto-enable for org members (`autoEnableOrganizationMembers: true`) | New member accounts not auto-enrolled |

**Critical:** ASDD monitors buckets but does NOT deep-scan every object.
For high-sensitivity buckets, ASDD alone is insufficient.

## Step 3 — Classification jobs and scoping

```bash
aws macie2 list-classification-jobs --region us-east-1 \
  --query 'items[*].{Name:name,Status:jobStatus,Type:jobType,LastRun:lastRunTime}' \
  --output table
```

| Job attribute | Healthy | Gap |
|---|---|---|
| `jobType` | ONE_TIME baseline + SCHEDULED ongoing | Only ONE_TIME → no ongoing coverage |
| `jobStatus` | RUNNING or COMPLETED | FAILED, CANCELLED → coverage gap |
| `scoping.includes` | Targets known sensitive buckets | No includes → scans everything or nothing |
| `scoping.excludes` | Excludes non-sensitive (logs, temp) | No excludes → cost + noise |
| `sampleDeep` | false for high-sensitivity (full scan) | true (sampled) for high-sensitivity → may miss data |
| `scheduleFrequency` | Daily for critical, weekly for high | Monthly/never for critical → stale coverage |

**Coverage gap calculation:**

```text
  S3 estate:  120 buckets
  ASDD monitors: 85 buckets
  Job-A deep-scans: 20 buckets (scheduled daily)
  Job-B deep-scans: 10 buckets (one-time)
  Gap: 35 buckets monitored by ASDD only (sampled, not deep-scanned)
       35 buckets NOT monitored at all
```

## Step 4 — Managed data identifiers

| Category | Examples |
|---|---|
| PII | Names, email, phone, address, SSN, passport |
| Financial | Credit card (Luhn-validated), bank account, routing |
| Credentials | AWS access keys, private keys, API tokens, JWT |
| Healthcare | Medical record numbers, health insurance (HIPAA) |

```bash
aws macie2 list-managed-data-identifiers --region us-east-1 \
  --query 'managedDataIdentifiers[*].{Category:category,Id:id}' --output table
```

**Common gap:** a job with `managedDataIdentifierSelector: RECOMMENDED`
excludes specialized detectors. For healthcare/financial orgs, use `ALL`.

## Step 5 — Custom data identifiers

```bash
aws macie2 list-custom-data-identifiers --region us-east-1 \
  --query 'customDataIdentifiers[*].{Name:name,Id:id}' --output table
```

| Check | Healthy | Gap |
|---|---|---|
| Exists for org-specific data | Employee ID, internal token, proprietary format | No custom identifiers → org-specific data undetected |
| Regex scoped (boundaries, bounded quantifiers) | `\bEMP-\d{6}\b` | `\d{1,19}` → false-positive flood |
| Ignore-words configured | `["example","test"]` | No ignore-words → test data flagged |
| Referenced by classification job(s) | Job `customDataIdentifierIds` includes CDI ID | Orphaned → never used in scan |

## Step 6 — Finding types and severities

| Category | Type prefix | Examples |
|---|---|---|
| Sensitive data | `SensitiveData:S3Object/` | `/CreditCard`, `/AwsCredentials`, `/Ssn`, `/ApiKey`, `/CustomIdentifier` |
| Policy | `Policy:IAMUser/S3` | `/BucketPublic`, `/BucketSharedExternally`, `/BucketReplicationExternal` |

**Healthy finding posture:** High severity near-zero (actively triaged),
Medium tracked with downward trend, Low reviewed and archived.
Suppressed findings <10% of total. Zero findings ever = Macie enabled
but scanning nothing.

## Step 7 — Suppression rules (findings filters)

```bash
aws macie2 list-findings-filters --region us-east-1 \
  --query 'findingIds[*].{Name:name,Action:action}' --output table
```

| Filter attribute | Healthy | Red flag |
|---|---|---|
| `action` | ARCHIVE (keeps findable) | SUPPRESS (hides from SH + CWE) |
| `criteria` scope | Narrow (specific bucket, type) | Broad (all types, all buckets) |
| High severity suppressed | No | Suppressing HIGH = red flag |
| Filter count | 3-10 (targeted) | 50+ (suppression sprawl) |

**Critical:** a filter with `action: SUPPRESS` that suppresses all High
severity findings is the most dangerous anti-pattern — the dashboard
shows zero findings, Security Hub receives nothing, the org believes it
has no sensitive data exposure.

## Step 8 — Multi-account Macie topology

```bash
aws macie2 list-members --region us-east-1 \
  --query 'members[*].{AccountId:accountId,Status:relationshipStatus}' --output table
```

| Check | Healthy | Gap |
|---|---|---|
| Administrator designated | Delegated admin account exists | No admin → each account independent |
| All org accounts enrolled | Member list matches org account list | Missing members → unmonitored |
| Member status ENABLED | `relationshipStatus` is ENABLED | PAUSED/INVITED/DISASSOCIATED → gap |
| ASDD auto-enable | `autoEnableOrganizationMembers: true` | New accounts not auto-enrolled |

**Coverage gap:**

```text
  Org accounts: 150  | Members: 142  | Gap: 8 unmonitored
  Of 142: ENABLED=135, PAUSED=5, INVITED=2
  Effective coverage: 135/150 = 90% → PARTIALLY_CLASSIFIED
```

## Step 9 — Security Hub and CloudWatch Events integration

```bash
# Check Security Hub for Macie findings
aws securityhub get-findings \
  --filters '{"ProductName":[{"Value":"Macie","Comparison":"EQUALS"}]}' \
  --region us-east-1 --query 'Findings[*].{Id:Id,Severity:Severity.Severity}' \
  --output table | head -10

# Check EventBridge rules
aws events list-rules --region us-east-1 \
  --query 'Rules[?contains(EventPattern,`Macie Finding`)].{Name:Name,State:State}' --output table
```

| Integration | Healthy | Gap |
|---|---|---|
| Security Hub export | Macie findings visible in SH | Export OFF → findings siloed in Macie console |
| EventBridge rule | Rule exists, target active | No rule → no automated response |
| Finding latency | FIFTEEN_MINUTES | SIX_HOURS → slow detection |

**Critical gap:** Macie is working, findings are generated — but SH
export is off and no EventBridge rule exists. Findings exist ONLY in the
Macie console. The SOC monitoring Security Hub sees nothing. This is the
#1 integration gap.

## Step 10 — Sampling depth vs full scan

| Configuration | Coverage | Audit implication |
|---|---|---|
| `sampleDeep: false` (full scan) | All objects scanned | Gold standard for high-sensitivity |
| `sampleDeep: true` (sampled) | Subset scanned | Acceptable for low-sensitivity, gap for high |
| ASDD only (no jobs) | Sampled by Macie | Lowest coverage — baseline discovery only |

| Bucket sensitivity | Required depth | ASDD sufficient? | Job required? |
|---|---|---|---|
| Critical (credentials) | Full scan, daily | No | Yes (daily, full) |
| High (PII, financial) | Full scan, weekly | No | Yes (weekly, full) |
| Medium (app data) | Sampled OK | Marginal | Recommended |
| Low (logs, temp) | ASDD baseline | Yes | No |

## Recent features

- **ASDD general availability (2023-2024):** Automatic S3 bucket
  discovery without explicit jobs. Default for new Macie enablements.
- **Expanded managed identifiers (2023-2024):** Additional PII types for
  APAC and EMEA regions (healthcare, financial formats).
- **Enhanced suppression criteria (2024-2025):** Findings filters now
  support granular criteria including `resourceS3BucketArn` patterns and
  `customDataIdentifiers.detections`.
- **Multi-account ASDD auto-enable (2024-2025):** New member accounts
  auto-enrolled in ASDD on association with `autoEnableOrganizationMembers`.
- **Audit Manager integration (2024-2025):** Macie findings feed into
  Audit Manager assessments for HIPAA, GDPR, PCI-DSS compliance evidence.
- **Classification engine optimization (2025-2026):** Up to 40% faster
  job runtime for large S3 estates.

## NEVER do these things

1. **NEVER declare CLASSIFIED based solely on Macie enablement.**
   Enablement is the floor. Without ASDD, scoped jobs, and Security Hub
   export, enablement provides zero coverage.

2. **NEVER assume ASDD provides full-scan coverage.** ASDD samples
   objects. High-sensitivity data needs scheduled jobs with full-scan
   depth. ASDD is discovery, not deterministic classification.

3. **NEVER approve a suppression rule without reviewing its scope.** A
   `SUPPRESS` filter on broad criteria masks real findings. Never
   suppress HIGH severity without an explicit documented exception.

4. **NEVER assume custom identifiers are well-constructed.** Regex with
   catastrophic backtracking or unbounded quantifiers causes job
   timeouts and false-positive floods. Always score regex quality.

5. **NEVER audit Macie in a single Region and declare org-wide coverage.**
   Macie is regional. An org operating in multiple Regions needs Macie
   enabled and audited in EACH Region.

6. **NEVER assume Security Hub integration is automatic.** Export must
   be explicitly enabled per Region. Without it, findings exist only in
   the Macie console.

7. **NEVER ignore member account status in multi-account Macie.** Members
   in PAUSED, INVITED, or DISASSOCIATED states are not being scanned.

8. **NEVER assume a one-time job provides ongoing coverage.** Without a
   SCHEDULED job, new objects are unclassified after the one-time scan.

9. **NEVER skip the bucket coverage gap calculation.** The delta between
   total buckets, ASDD-monitored, and job-scoped is the #1 coverage metric.

10. **NEVER assume EventBridge rules are firing.** A rule may exist but
    have a broken target (deleted Lambda). Always verify the target.

## Output format

```text
MACIE_CLASSIFICATION: <account-id> (<region>) — <macie-status>
VERDICT: CLASSIFIED | PARTIALLY_CLASSIFIED | UNCLASSIFIED
CHECKLIST:
  [✓|✗] Macie session: ENABLED | PAUSED | NOT_ENABLED
  [✓|✗] Finding frequency: <frequency>
  [✓|✗] Automated discovery (ASDD): ENABLED | DISABLED
  [✓|✗] ASDD auto-enable members: true | false
  [✓|✗] Classification jobs: <count> (one-time: <n>, scheduled: <n>)
  [✓|✗] Coverage gap: <total> total, <asdd> ASDD, <deep-scan> deep-scan, <gap> unmonitored
  [✓|✗] Managed identifiers: ALL | RECOMMENDED | PARTIAL
  [✓|✗] Custom identifiers: <count> (scored: <healthy>/<review>/<risk>)
  [✓|✗] High-sensitivity deep-scan: <n>/<n> buckets
  [✓|✗] Findings (last 30d): <high> High, <medium> Medium, <low> Low
  [✓|✗] Suppression rules: <count> (SUPPRESS: <n>, ARCHIVE: <n>)
  [✓|✗] Suppression scope: narrow | BROAD
  [✓|✗] Multi-account: <members-enabled>/<org-accounts> accounts enrolled
  [✓|✗] Security Hub export: ENABLED | DISABLED
  [✓|✗] EventBridge rule: active | missing | target-broken
  [✓|✗] Sampling depth: high-sensitivity full-scan | ASDD-only (gap)
VERIFICATION_COMMANDS:
  aws macie2 get-macie-session --region <region>
  aws macie2 get-automated-discovery-configuration --region <region>
  aws macie2 list-classification-jobs --region <region>
  aws macie2 list-findings-filters --region <region>
  aws macie2 list-members --region <region>
```

### Worked example — healthy posture (CLASSIFIED)

```text
MACIE_CLASSIFICATION: 123456789012 (us-east-1) — ENABLED
VERDICT: CLASSIFIED
CHECKLIST:
  [✓] Macie session: ENABLED
  [✓] Finding frequency: FIFTEEN_MINUTES
  [✓] Automated discovery (ASDD): ENABLED
  [✓] ASDD auto-enable members: true
  [✓] Classification jobs: 4 (one-time: 1, scheduled: 3)
  [✓] Coverage gap: 120 total, 108 ASDD, 28 deep-scan, 12 unmonitored (low-risk)
  [✓] Managed identifiers: ALL
  [✓] Custom identifiers: 3 (scored: 3/0/0)
  [✓] High-sensitivity deep-scan: 12/12 buckets (daily full-scan)
  [✓] Findings (last 30d): 2 High (triaged), 8 Medium, 15 Low (archived)
  [✓] Suppression rules: 4 (SUPPRESS: 1, ARCHIVE: 3)
  [✓] Suppression scope: narrow (no High severity suppressed)
  [✓] Multi-account: 148/150 accounts enrolled
  [✓] Security Hub export: ENABLED
  [✓] EventBridge rule: active (target: macie-auto-remediation Lambda)
  [✓] Sampling depth: high-sensitivity full-scan
VERIFICATION_COMMANDS:
  aws macie2 get-macie-session --region us-east-1
  aws macie2 get-automated-discovery-configuration --region us-east-1
  aws macie2 list-classification-jobs --region us-east-1
  aws macie2 list-findings-filters --region us-east-1
  aws macie2 list-members --region us-east-1
```

## Domain

AWS CloudOps / Amazon Macie Data Discovery & Classification Posture
Assessment.

## AWS documentation

- **Amazon Macie** — https://docs.aws.amazon.com/macie/latest/user/what-is-macie.html
- **Automated sensitive data discovery** — https://docs.aws.amazon.com/macie/latest/user/automated-discovery.html
- **Classification jobs** — https://docs.aws.amazon.com/macie/latest/user/classification-jobs.html
- **Managed data identifiers** — https://docs.aws.amazon.com/macie/latest/user/managed-data-identifiers.html
- **Custom data identifiers** — https://docs.aws.amazon.com/macie/latest/user/custom-data-identifiers.html
- **Findings and filters** — https://docs.aws.amazon.com/macie/latest/user/findings.html
- **Multi-account management** — https://docs.aws.amazon.com/macie/latest/user/accounts.html
- **Security Hub integration** — https://docs.aws.amazon.com/macie/latest/user/macie-security-hub.html
