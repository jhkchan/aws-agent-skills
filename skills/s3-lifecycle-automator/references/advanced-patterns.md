# Advanced Patterns — s3-lifecycle-automator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

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

---

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

---

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

---

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
