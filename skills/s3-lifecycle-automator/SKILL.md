---
name: s3-lifecycle-automator
description: Designs and implements automated S3 lifecycle policy deployment across single and multi-account environments. Covers tag-based lifecycle policy deployment via CloudFormation StackSets and Lambda, bucket inventory collection for lifecycle audit, automated storage class transitions (Standard to IA to Glacier to Deep Archive) based on object age patterns, versioning lifecycle rules (NoncurrentVersionTransition and NoncurrentVersionExpiration), Intelligent-Tiering opt-in automation, Storage Lens analysis for identifying buckets without lifecycle policies, S3 Batch Operations for retroactive storage-class tiering of existing objects, lifecycle policy validation enforcing minimum-days rules per tier (30 days for IA, 90 days for Glacier Instant Retrieval), multi- account lifecycle enforcement via StackSets, and EventBridge notifications on lifecycle policy changes. Emits AUTOMATION_DEPLOYED with a fully validated lifecycle configuration or REVIEW_REQUIRED with the specific validation gap. Use when building S3...
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws s3api put-bucket-lifecycle-configuration, get-bucket-lifecycle- configuration, put-bucket-intelligent-tiering-configuration, aws s3control create-job, get-storage-lens-configuration, and aws cloudformation create-stack-set, create-stack-instances — AWS CLI v2, SSO or key-based credentials.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Building S3 lifecycle automation, deploying tiering policies (Standard to IA to Glacier to Deep Archive), setting up versioning lifecycle rules (NoncurrentVersionTransition, NoncurrentVersionExpiration), enabling Intelligent-Tiering at scale, remediating Storage Lens gaps, running S3 Batch Operations for retroactive tiering, validating lifecycle min-days rules, or deploying multi-account lifecycle via StackSets.
  activation_triggers: automate S3 lifecycle policy, deploy lifecycle StackSets, put-bucket-lifecycle-configuration, Standard to IA to Glacier transition, NoncurrentVersionTransition, Intelligent-Tiering opt-in, S3 Batch Operations tiering, Storage Lens lifecycle gap, lifecycle min-days validation, multi-account lifecycle enforcement
  invocation_schema: 'Input: either (a) an S3 lifecycle requirement ("transition objects to IA after 30 days, Glacier after 90 days", "expire non-current versions after 60 days"), OR (b) a Storage Lens report identifying buckets without lifecycle policies. Output: deterministic LIFECYCLE block per bucket — POLICY/TRANSITIONS/VERSIONING/VALIDATION/ENFORCEMENT/ VERDICT — where VERDICT is AUTOMATION_DEPLOYED (policy validated and ready) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: S3 lifecycle, lifecycle policy, storage class transition, Standard to IA, Glacier, Deep Archive, Intelligent-Tiering, NoncurrentVersionTransition, NoncurrentVersionExpiration, S3 Batch Operations, Storage Lens, CloudFormation StackSets, lifecycle validation, min-days rules, multi-account lifecycle, tag-based lifecycle
  tags: aws-s3, s3-lifecycle, storage-tiering, intelligent-tiering, storage-lens, batch-operations, automate
---

# S3 Lifecycle Automator

## Mindset

**One-line takeaway:** S3 lifecycle automation is a four-stage pipeline —
**inventory** (identify buckets and object-age patterns) → **design**
(lifecycle rules with correct transition days per tier) → **validate**
(enforce min-days: 30 for IA, 90 for Glacier IR) → **deploy**
(put-bucket-lifecycle-configuration or StackSets). A gap in ANY stage
produces silent cost leakage.

- **Design** without **validation** is fragile: S3 silently rejects rules
  that violate min-days constraints. A rule transitioning to IA at 15
  days is accepted by the API but never executes.
- **Lifecycle min-days per tier is enforced.** Standard to Standard-IA
  requires 30 days. Standard-IA to Glacier Instant Retrieval requires
  90 days total object age. These are hard constraints.
- **Versioning lifecycle is SEPARATE from current-version rules.**
  `NoncurrentVersionTransition` and `NoncurrentVersionExpiration` operate
  on non-current versions only. A policy that only transitions current
  versions leaves all deleted-object versions in Standard forever.

## Quick navigation

| You want to... | Go to |
|---|---|
| Design Standard→IA→Glacier→DeepArchive policy | Step 2 + Appendix A |
| Validate min-days rules | Step 3 + Step 9 |
| Add versioning lifecycle rules | Step 4 |
| Enable Intelligent-Tiering | Step 5 |
| Deploy via StackSets (multi-account) | Step 6 |
| Find buckets without lifecycle via Storage Lens | Step 7 |
| Retroactive tiering via Batch Operations | Step 8 |
| Add EventBridge notifications on changes | Step 10 |
| Avoid common pitfall patterns | Anti-Patterns |

## Critical rules at a glance (do NOT bury these)

1. **Lifecycle min-days per tier is a HARD constraint.** Minimum for
   Standard-IA is 30 days. For Glacier Instant Retrieval, 90 days total
   object age. For Deep Archive, 180 days total. A rule with `Days: 15`
   for IA is silently accepted but NEVER executes.

2. **Versioning lifecycle rules are SEPARATE from current-version
   rules.** `NoncurrentVersionTransition` and
   `NoncurrentVersionExpiration` operate exclusively on non-current
   versions. Without them, non-current versions accumulate in Standard
   indefinitely.

3. **`put-bucket-lifecycle-configuration` REPLACES the entire policy.**
   No append mode. Always `get-bucket-lifecycle-configuration` first,
   merge, then PUT.

4. **Intelligent-Tiering has no transition-day minimums.** Auto-moves
   objects between access tiers based on access patterns. Key advantage
   for buckets with unpredictable access.

5. **Storage Lens identifies buckets without lifecycle policies at
   scale.** The `LifecycleEnabled` metric shows which buckets lack
   configuration. Use as the inventory input for multi-bucket deployment.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Bucket name(s) | `aws s3api list-buckets` | Target for lifecycle |
| Current lifecycle | `aws s3api get-bucket-lifecycle-configuration` | Don't overwrite blindly |
| Versioning status | `aws s3api get-bucket-versioning` | Determines NoncurrentVersion rules |
| Object age distribution | Storage Lens or S3 Inventory | Drives transition day selection |
| Storage Lens report | `aws s3control get-storage-lens-configuration` | Identifies gaps |
| Account list (multi-account) | `aws organizations list-accounts` | For StackSets |
| StackSet status | `aws cloudformation list-stack-instances` | Verify rollout |

**If the input is malformed**, emit:

```text
LIFECYCLE: <reference>
BUCKET: <bucket-name>
VERDICT: ERROR
REASON: Cannot design lifecycle policy — bucket name and transition schedule are required.
GAP: Re-supply bucket name, versioning status, and desired transition days per storage class.
```

## Process — Lifecycle design (apply in order)

### Step 0: Expert knowledge — non-obvious S3 lifecycle behaviors

- **Min-days constraints are silently enforced.** The
  `put-bucket-lifecycle-configuration` API accepts rules that violate
  min-days WITHOUT error. The rule appears in GET output but never
  executes. Enforced minimums:

  | Transition | Minimum days |
  |---|---|
  | Standard → Standard-IA | 30 days |
  | Standard-IA → Glacier Instant Retrieval | 90 days total object age |
  | Standard-IA → Glacier Flexible Retrieval | 91 days total (1 day after IA) |
  | Any → Deep Archive | 180 days total object age |
  | Standard → Glacier Flexible (direct) | 1 day |

- **NoncurrentVersionTransition/Expiration are the ONLY way to manage
  non-current versions.** When versioning is enabled, deleting an object
  creates a delete marker; the prior version becomes non-current.
  Without NoncurrentVersion rules, these accumulate forever.

- **`put-bucket-lifecycle-configuration` is a full replacement.** Always
  GET, merge, PUT. This is the most common cause of "my old lifecycle
  rules disappeared."

- **Filter precedence matters.** A rule with `Filter: {Prefix: 'logs/'}`
  applies only to `logs/`. A rule with no filter applies to ALL objects.
  Overlapping rules with conflicting transitions produce undefined
  behavior. Design non-overlapping filters.

- **Intelligent-Tiering has auto-tiering with no day configs.** Objects
  auto-move between Frequent Access, Infrequent Access, Archive Instant,
  Archive, and Deep Archive tiers based on access patterns. Archive
  Instant requires 90 days consecutive non-access.

- **S3 Batch Operations can retroactively change storage class.**
  `CreateJob` with `S3SetStorageClass` moves existing objects. This is
  the remediation path for objects that a new lifecycle policy only
  applies to going forward.

- **Lifecycle rules apply prospectively but catch existing objects on
  the next daily cycle.** Objects already older than the transition day
  are transitioned within 24 hours of policy deployment.

- **Glacier Instant Retrieval (IR) and Glacier Flexible Retrieval are
  DIFFERENT storage classes.** IR has millisecond latency and 90-day
  minimum. Flexible Retrieval has minutes-to-hours latency and 1-day
  minimum after IA.

- **StackSets deploy lifecycle across accounts and regions.** The
  StackSet administration role needs `s3:PutBucketLifecycleConfiguration`
  in each target account.

### Step 1: Classify the lifecycle requirement

| Requirement | Pattern | Transition schedule |
|---|---|---|
| Log archival | Standard→IA→Glacier→DeepArchive | 30d→90d→180d→365d |
| Backup retention | Standard→IA→Glacier IR | 30d→90d |
| Temporary uploads | Standard→Expire | 30d expire |
| Versioned data | Current: Standard→IA; Noncurrent: IA→Expire | 30d current, 60d noncurrent |
| Unknown access pattern | Intelligent-Tiering opt-in | Auto-tiering |
| Compliance archive | Standard→DeepArchive | 180d |

If the access pattern is unknown, default to Intelligent-Tiering.

### Step 2: Design the lifecycle policy

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-logs-bucket \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "log-archival-policy",
        "Status": "Enabled",
        "Filter": {"Prefix": "logs/"},
        "Transitions": [
          {"Days": 30, "StorageClass": "STANDARD_IA"},
          {"Days": 90, "StorageClass": "GLACIER_IR"},
          {"Days": 180, "StorageClass": "GLACIER"},
          {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
        ]
      }
    ]
  }'
```

Tag-based lifecycle rule:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-data-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "archive-tagged-objects",
      "Status": "Enabled",
      "Filter": {"Tag": {"Key": "ArchiveClass", "Value": "glacier"}},
      "Transitions": [{"Days": 1, "StorageClass": "GLACIER"}]
    }]
  }'
```

### Step 3: Validate min-days rules

Before deploying, validate every transition against enforced minimums:

| From | To | Min days (total object age) | Notes |
|---|---|---|---|
| STANDARD | STANDARD_IA | 30 | Hard minimum |
| STANDARD_IA | GLACIER_IR | 90 | Must be >= 90 total |
| STANDARD_IA | GLACIER | 91 (1 day after IA) | 30 (IA) + 61 |
| STANDARD | GLACIER (direct) | 1 | Can skip IA |
| Any | DEEP_ARCHIVE | 180 | Hard minimum |
| STANDARD | ONEZONE_IA | 30 | Same as STANDARD_IA |
| STANDARD | INTELLIGENT_TIERING | 0 | No minimum |

If ANY transition violates the minimum, emit:

```text
LIFECYCLE: <reference>
BUCKET: <bucket-name>
RULE: <rule-id>
TRANSITION: STANDARD → STANDARD_IA
CONFIGURED_DAYS: 15
MINIMUM_DAYS: 30
VERDICT: REVIEW_REQUIRED
GAP: Transition to STANDARD_IA requires minimum 30 days. Configured 15 days will be silently accepted but NEVER execute.
```

### Step 4: Add versioning lifecycle rules

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-versioned-bucket \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "versioned-lifecycle-policy",
        "Status": "Enabled",
        "Filter": {},
        "Transitions": [
          {"Days": 30, "StorageClass": "STANDARD_IA"},
          {"Days": 90, "StorageClass": "GLACIER_IR"}
        ],
        "NoncurrentVersionTransitions": [
          {"NoncurrentDays": 30, "StorageClass": "STANDARD_IA"},
          {"NoncurrentDays": 90, "StorageClass": "GLACIER"}
        ],
        "NoncurrentVersionExpiration": {"NoncurrentDays": 120},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
        "ExpiredObjectDeleteMarker": true
      }
    ]
  }'
```

| Field | What it does |
|---|---|
| `NoncurrentVersionTransitions` | Transition non-current versions to cheaper storage |
| `NoncurrentVersionExpiration` | Permanently delete non-current versions after N days |
| `AbortIncompleteMultipartUpload` | Abort uploads incomplete within N days |
| `ExpiredObjectDeleteMarker` | Remove delete marker when it's the only version |

### Step 5: Enable Intelligent-Tiering

```bash
# Opt-in via lifecycle rule (Days: 0 = immediate transition to IT)
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-data-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "intelligent-tiering-all-objects",
      "Status": "Enabled",
      "Filter": {},
      "Transitions": [{"Days": 0, "StorageClass": "INTELLIGENT_TIERING"}]
    }]
  }'

# Configure archive tiers (optional)
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket my-data-bucket \
  --id ArchiveConfig \
  --intelligent-tiering-configuration '{
    "Id": "ArchiveConfig",
    "Status": "Enabled",
    "Tierings": [
      {"AccessTier": "ARCHIVE_ACCESS", "Days": 90},
      {"AccessTier": "DEEP_ARCHIVE_ACCESS", "Days": 180}
    ]
  }'
```

| IT tier | Auto-transition trigger | Retrieval |
|---|---|---|
| Frequent Access | Accessed within 30 days | Milliseconds |
| Infrequent Access | Not accessed 31+ days | Milliseconds |
| Archive Instant | Not accessed 90+ days | Milliseconds |
| Archive | Configurable (default 90) | Minutes to hours |
| Deep Archive | Configurable (default 180) | Up to 12 hours |

### Step 6: Multi-account deployment via StackSets

```yaml
# lifecycle-stackset.yaml
AWSTemplateFormatVersion: '2010-09-09'
Parameters:
  BucketName:
    Type: String
    Default: access-logs-bucket
Resources:
  LifecyclePolicy:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref BucketName
      LifecycleConfiguration:
        Rules:
          - Id: log-archival
            Status: Enabled
            Transitions:
              - StorageClass: STANDARD_IA
                TransitionInDays: 30
              - StorageClass: GLACIER_IR
                TransitionInDays: 90
              - StorageClass: DEEP_ARCHIVE
                TransitionInDays: 180
            NoncurrentVersionExpirationInDays: 120
            AbortIncompleteMultipartUpload:
              DaysAfterInitiation: 7
```

```bash
aws cloudformation create-stack-set \
  --stack-set-name s3-lifecycle-baseline \
  --template-body file://lifecycle-stackset.yaml \
  --permission-model SERVICE_MANAGED \
  --auto-deployment '{"Enabled": true, "RetainStacksOnAccountRemoval": false}' \
  --capabilities CAPABILITY_IAM

aws cloudformation create-stack-instances \
  --stack-set-name s3-lifecycle-baseline \
  --deployment-targets '{"OrganizationalUnitIds": ["ou-xxxx-xxxxxxxx"]}'
```

Lambda alternative for tag-based bucket targeting — iterate buckets by
tag and deploy lifecycle via `put-bucket-lifecycle-configuration`.

### Step 7: Identify lifecycle gaps via Storage Lens

```bash
aws s3control get-storage-lens-configuration \
  --config-id org-storage-lens \
  --account-id 111111111111
```

| Metric | What it reveals | Action |
|---|---|---|
| `LifecycleEnabled` | Buckets with lifecycle policy | Deploy to the gap |
| `StorageClass` distribution | Objects by storage class | If 90%+ Standard, lifecycle missing |
| `ObjectAge` distribution | Objects by age bucket | Drives transition day selection |
| `NoncurrentVersionStorage` | Non-current version storage | Drives NoncurrentVersionExpiration |

### Step 8: Retroactive tiering via S3 Batch Operations

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3SetStorageClass": {"TargetStorageClass": "GLACIER_IR"}}' \
  --report '{"Bucket": "arn:aws:s3:::batch-ops-reports", "Format": "Report_CSV_20180820", "Enabled": true}' \
  --manifest '{"Spec": {"Format": "S3BatchOperations_CSV_20180820", "Fields": ["Bucket", "Key"]}, "Location": {"ObjectArn": "arn:aws:s3:::batch-ops-manifests/manifest.csv"}}' \
  --priority 10 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsRole
```

Monitor: `aws s3control describe-job --account-id 111111111111 --job-id <id>`

### Step 9: Pre-deployment validation function

```python
MIN_DAYS = {
    ('STANDARD', 'STANDARD_IA'): 30,
    ('STANDARD', 'ONEZONE_IA'): 30,
    ('STANDARD_IA', 'GLACIER_IR'): 90,
    ('STANDARD_IA', 'GLACIER'): 91,
    ('STANDARD', 'GLACIER'): 1,
    ('STANDARD', 'GLACIER_IR'): 90,
    ('GLACIER', 'DEEP_ARCHIVE'): 180,
    ('STANDARD', 'DEEP_ARCHIVE'): 180,
}

def validate_lifecycle(config):
    errors = []
    for rule in config.get('Rules', []):
        if rule.get('Status') != 'Enabled':
            continue
        prev_class = 'STANDARD'
        for t in rule.get('Transitions', []):
            key = (prev_class, t['StorageClass'])
            min_required = MIN_DAYS.get(key, 0)
            if t['Days'] < min_required:
                errors.append(f"Rule '{rule['ID']}': {prev_class}->{t['StorageClass']} "
                              f"configured {t['Days']} days, minimum is {min_required}.")
            prev_class = t['StorageClass']
    return errors
```

### Step 10: EventBridge notifications on lifecycle changes

```bash
aws events put-rule \
  --name s3-lifecycle-change \
  --event-pattern '{
    "source": ["aws.s3"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventName": ["PutBucketLifecycleConfiguration", "DeleteBucketLifecycle"],
      "eventSource": ["s3.amazonaws.com"]
    }
  }'

aws events put-targets \
  --rule s3-lifecycle-change \
  --targets '[{"Id":"lifecycle-monitor","Arn":"arn:aws:lambda:us-east-1:111111111111:function:s3-lifecycle-monitor"}]'
```

## Output format

```text
LIFECYCLE: <reference>
BUCKET: <bucket-name>
POLICY:
  - Rule ID: <rule-id>
  - Status: Enabled
  - Filter: <prefix, tag, or all>
TRANSITIONS:
  - Standard → Standard-IA: <days> days (min 30)
  - Standard-IA → Glacier IR: <days> days (min 90)
VERSIONING:
  - NoncurrentVersionTransition: <days> → <storage class>
  - NoncurrentVersionExpiration: <days>
VALIDATION:
  - Min-days check: PASS | FAIL
  - Overlap check: PASS | FAIL
ENFORCEMENT:
  - Deployment: direct-CLI | StackSet | Lambda-tag-based
  - Accounts: <list or "single">
  - EventBridge: <rule ARN or "NOT WIRED">
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet for the lifecycle configuration>
```

### Worked example — AUTOMATION_DEPLOYED, log archival with versioning

```text
LIFECYCLE: log-archival-baseline
BUCKET: app-access-logs
POLICY:
  - Rule ID: log-archival-policy
  - Status: Enabled
  - Filter: Prefix "logs/"
TRANSITIONS:
  - Standard → Standard-IA: 30 days (min 30) — PASS
  - Standard-IA → Glacier IR: 90 days (min 90) — PASS
  - Glacier IR → Deep Archive: 365 days (min 180) — PASS
VERSIONING:
  - NoncurrentVersionTransition: 30 days → STANDARD_IA
  - NoncurrentVersionExpiration: 120 days
  - AbortIncompleteMultipartUpload: 7 days
VALIDATION:
  - Min-days check: PASS
  - Overlap check: PASS
ENFORCEMENT:
  - Deployment: direct-CLI
  - Accounts: single (111111111111)
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws s3api put-bucket-lifecycle-configuration --bucket app-access-logs --lifecycle-configuration '{"Rules":[{"ID":"log-archival-policy","Status":"Enabled","Filter":{"Prefix":"logs/"},"Transitions":[{"Days":30,"StorageClass":"STANDARD_IA"},{"Days":90,"StorageClass":"GLACIER_IR"},{"Days":365,"StorageClass":"DEEP_ARCHIVE"}],"NoncurrentVersionTransitions":[{"NoncurrentDays":30,"StorageClass":"STANDARD_IA"}],"NoncurrentVersionExpiration":{"NoncurrentDays":120},"AbortIncompleteMultipartUpload":{"DaysAfterInitiation":7}}]}'
```

### Worked example — REVIEW_REQUIRED, invalid min-days

```text
LIFECYCLE: invalid-transition-days
BUCKET: data-archive
POLICY:
  - Rule ID: archive-policy
  - Status: Enabled
  - Filter: all objects
TRANSITIONS:
  - Standard → Standard-IA: 15 days (min 30) — FAIL
  - Standard-IA → Glacier IR: 60 days (min 90) — FAIL
VERSIONING:
  - NoncurrentVersionExpiration: NOT CONFIGURED
VALIDATION:
  - Min-days check: FAIL (2 violations)
ENFORCEMENT:
  - Deployment: NOT DEPLOYED (validation blocked)
VERDICT: REVIEW_REQUIRED
GAP: Two min-days violations. (1) Standard→Standard-IA at 15 days: minimum is 30. API will accept but NEVER execute. Set to 30+. (2) Standard-IA→Glacier IR at 60 days: minimum is 90. Set to 90+. Also add NoncurrentVersionExpiration if versioning is enabled.
TEMPLATE: (corrected — set Days to 30 and 90 respectively, then re-deploy)
```

## Anti-Patterns — NEVER do these things

- NEVER deploy lifecycle rules with transition days below the enforced
  minimum without validation. The API accepts invalid rules silently.
  Objects remain in the original storage class and costs never decrease.

- NEVER call `put-bucket-lifecycle-configuration` without first calling
  `get-bucket-lifecycle-configuration`. PUT is a full replacement. A
  call with one new rule silently deletes all existing rules.

- NEVER omit NoncurrentVersionExpiration on versioned buckets. Without
  it, every deleted-object version accumulates in Standard indefinitely.
  This is the single most common cause of "S3 costs keep growing despite
  lifecycle policies."

- NEVER confuse Glacier Instant Retrieval (millisecond latency, 90-day
  min) with Glacier Flexible Retrieval (minutes-hours latency, 1-day
  min after IA). Choosing wrong produces excessive retrieval costs or
  inaccessible data.

- NEVER deploy lifecycle policies to production without testing on a
  non-production bucket first. A misconfigured expiration rule deletes
  objects permanently.

- NEVER use overlapping lifecycle rules with conflicting transitions.
  Design rules with non-overlapping filters.

- NEVER omit `AbortIncompleteMultipartUpload` on buckets that receive
  multipart uploads. Orphaned parts are billed at Standard and are NOT
  visible in the standard object listing.

- NEVER deploy StackSets without verifying the administration role has
  `s3:PutBucketLifecycleConfiguration` in each target account.

- NEVER assume Intelligent-Tiering is always cheaper. It charges a
  monitoring fee ($0.0025 per 1,000 objects). For small objects with
  predictable access, explicit transitions may be cheaper.

- NEVER set `ExpiredObjectDeleteMarker: true` without understanding the
  consequence. It removes the delete marker when it's the only version,
  making the object name available for reuse.

- NEVER forget to validate after deployment. `get-bucket-lifecycle-
  configuration` shows the policy but does NOT confirm rules are
  executing. Monitor Storage Lens `StorageClass` distribution over time.

- NEVER use S3 Batch Operations without a test run on a small manifest
  first. `S3SetStorageClass` changes are irreversible.

- NEVER omit the Batch Operations report. Without `Report.Enabled: true`,
  there is no audit trail of which objects were tiered.

## Pre-flight safety checks (run before applying any lifecycle CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit: `CONFIRM: About to <action> for bucket <bucket>. Proceed? (yes/no)`

- **Back up current configuration** before modifying:
  `aws s3api get-bucket-lifecycle-configuration --bucket <bucket> >
  /tmp/<bucket>-lifecycle-backup-$(date +%s).json`

- **Before deploying expiration rules**, verify the filter prefix targets
  only intended objects. An empty prefix with `Expiration` deletes ALL.

- **Before StackSets deployment**, validate the template:
  `aws cloudformation validate-template --template-body file://lifecycle-stackset.yaml`

- **For Batch Operations**, start with 10 objects. Verify storage class
  changes before running the full manifest.

## Appendix A — Storage class reference

| Storage class | Use case | Retrieval | Min lifecycle days | Cost (vs Standard) |
|---|---|---|---|---|
| `STANDARD` | Frequently accessed | Milliseconds | N/A | 1x baseline |
| `STANDARD_IA` | Infrequent, long-lived | Milliseconds | 30 days | ~40% cheaper |
| `ONEZONE_IA` | Infrequent, non-critical | Milliseconds | 30 days | ~52% cheaper |
| `GLACIER_IR` | Archives, millisecond access | Milliseconds | 90 days | ~68% cheaper |
| `GLACIER` (Flexible) | Long-term archives | 1-5 min to hours | 1 day after IA | ~80% cheaper |
| `DEEP_ARCHIVE` | Compliance archives | 12 hours | 180 days | ~95% cheaper |
| `INTELLIGENT_TIERING` | Unknown access patterns | Milliseconds (FA/IA) | 0 days | Varies |

## Appendix B — Decision tree

```
Is the access pattern predictable?
├─ Yes → Retrieval latency requirement?
│        ├─ Milliseconds → Standard → IA (30d) → Glacier IR (90d)
│        └─ Minutes/hours → Standard → IA (30d) → Glacier (91d) → Deep Archive (180d)
└─ No  → Enable Intelligent-Tiering (auto-tiering, no day configs)

Versioning enabled?
├─ Yes → Add NoncurrentVersionTransition + Expiration + AbortMultipart
└─ No  → Current-version transitions + Expiration only

Multi-account?
├─ Yes → Deploy via CloudFormation StackSets
└─ No  → Direct CLI per bucket

Existing objects need immediate tiering?
├─ Yes → S3 Batch Operations (S3SetStorageClass)
└─ No  → Lifecycle rules handle going forward
```

## Recent AWS features (2024-2026)

- **Intelligent-Tiering Archive Instant tier (2024):** New auto-tier
  within Intelligent-Tiering that moves objects to archive after 90 days
  of no access with millisecond retrieval. Bridges IA and Glacier.

- **Glacier IR min-days clarification (2024-2025):** The 90-day minimum
  for Glacier IR applies to total object age, not days in the prior tier.

- **Storage Lens lifecycle metrics (2024-2025):** Enhanced metrics now
  include per-bucket lifecycle status and object-age distribution. The
  `LifecycleEnabled` metric directly identifies buckets without coverage.

- **S3 Batch Operations enhanced reporting (2024):** Per-object status
  in completion reports including failure reasons.

- **Lifecycle policy versioning via CloudTrail (2025):** Full lifecycle
  configuration payload captured on PutBucketLifecycleConfiguration
  events for audit-trail reconstruction.

## Expert heuristic: the silent lifecycle failure

The most dangerous pattern is the "invalid rule that deploys
successfully." An operator sets Standard→IA at 15 days. The API accepts
it. GET confirms the rule exists. Storage Lens shows lifecycle enabled.
Everything looks correct — but objects never transition because 15 days
violates the 30-day minimum.

**The rule (non-negotiable):**

> ALWAYS validate lifecycle transition days against enforced minimums
> BEFORE deployment. The API does not validate — it accepts and silently
> ignores. A rule that violates min-days is dead configuration that gives
> a false sense of cost optimization.

**Why this rule exists:** The S3 lifecycle engine evaluates rules daily.
When a transition day is below the minimum, the engine skips the
transition. No error is logged. No metric is emitted. The object sits
in Standard indefinitely while the operator believes lifecycle is active.

**Verification protocol:**

| Check | Command | Expected |
|---|---|---|
| Policy exists | `get-bucket-lifecycle-configuration` | Rules listed |
| Min-days valid | Pre-deploy validation (Step 9) | All PASS |
| Objects transitioning | Storage Lens `StorageClass` distribution | Non-Standard % increasing |
| Noncurrent expiring | Storage Lens `NoncurrentVersionStorage` | Decreasing |
| Multipart aborting | S3 Inventory `MultipartUpload` | No orphaned parts |

**Pre-production validation (3-cycle rule):**

1. **Cycle 1 — Non-prod test:** Deploy to a non-prod bucket with test
   objects. After 48 hours, verify storage class via S3 Inventory or
   `head-object`.
2. **Cycle 2 — Production test:** Deploy to one production bucket.
   Monitor Storage Lens for 1 week.
3. **Cycle 3 — Fleet rollout:** Deploy via StackSets. Monitor org-level
   dashboard for 2 weeks.

**Surface in the output:** include `VALIDATION_STATUS: <validated |
unvalidated>` and `COVERAGE_STATUS: <single-bucket | multi-account-
stackset | batch-ops-retroactive>`. If `VALIDATION_STATUS` is not
`validated`, do NOT mark the policy as deployable.

## Domain

AWS CloudOps / Storage Automation — S3 Lifecycle and Intelligent-Tiering.

## AWS documentation

- **S3 Lifecycle Configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **S3 Intelligent-Tiering** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html#sc-glacier-tiering
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **S3 Storage Lens** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens.html
- **Lifecycle Transition Considerations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html
