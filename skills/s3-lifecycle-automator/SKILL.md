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

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — non-obvious lifecycle behaviors deep dive.
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

→ Advanced pattern moved to [references/advanced-patterns.md](references/advanced-patterns.md) — multi-account StackSets deployment.
### Step 7: Identify lifecycle gaps via Storage Lens

→ Moved to [references/storage-lens-and-batch-operations.md](references/storage-lens-and-batch-operations.md).
### Step 8: Retroactive tiering via S3 Batch Operations

→ Moved to [references/storage-lens-and-batch-operations.md](references/storage-lens-and-batch-operations.md).
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

→ Secondary example moved to [references/worked-examples.md](references/worked-examples.md); the AUTOMATION_DEPLOYED example above is primary.
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

→ Storage class table moved to [references/storage-class-transition-rules.md](references/storage-class-transition-rules.md).
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

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md).
## Expert heuristic: the silent lifecycle failure

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — the silent lifecycle failure.
## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge, StackSets multi-account pattern, silent lifecycle failure, recent AWS features.
- [references/worked-examples.md](references/worked-examples.md) — secondary worked example (REVIEW_REQUIRED, invalid min-days).
- [references/storage-class-transition-rules.md](references/storage-class-transition-rules.md) — pre-existing; extended with Appendix A storage class reference.
- [references/storage-lens-and-batch-operations.md](references/storage-lens-and-batch-operations.md) — pre-existing; extended with Steps 7-8 (Storage Lens gaps, Batch Operations tiering).

## Domain

AWS CloudOps / Storage Automation — S3 Lifecycle and Intelligent-Tiering.

## AWS documentation

- **S3 Lifecycle Configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **S3 Intelligent-Tiering** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html#sc-glacier-tiering
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **S3 Storage Lens** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens.html
- **Lifecycle Transition Considerations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html
