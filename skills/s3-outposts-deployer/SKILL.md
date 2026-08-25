---
name: s3-outposts-deployer
description: 'Provisions Amazon S3 on Outposts with production defaults: S3 outpost bucket creation, endpoint (required for accessing S3 on Outpost from on-prem via VPC), access point (regional vs outpost), storage class (STANDARD only on Outpost — no IA, no GLACIER), versioning, lifecycle (transition to S3 on Outpost only, no cloud tier transition), replication (from Outpost to cloud S3, one-way only), object lock (WORM), encryption (SSE-S3 only, no KMS on Outpost), access via VPC endpoint, networking requirements (PrivateLink), CloudWatch metrics, and capacity management (Outpost storage is finite and physically constrained). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an S3 on Outposts bucket, configuring endpoints for on-prem access, setting up replication from Outpost to cloud, or managing. Triggers: s3 outposts, s3 on outpost, outpost bucket, s3 outpost endpoint, s3 outpost access point, s3 outpost replication, object lock outpost, s3 outpost capacity, s3 outpost encryption.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with s3control and ec2 access. Works with Terraform aws_s3control_bucket, aws_s3control_access_point, and aws_s3_outposts_endpoint resources and CloudFormation AWS::S3Outposts::* templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, s3-outposts, cloudops, deploy, storage, outposts, on-premises, hybrid
  dependencies: aws-orchestrator
  keywords: aws, s3 outposts, s3 on outpost, outpost bucket, outpost endpoint, s3 outpost access point, s3 outpost replication, object lock outpost, sse-s3 outpost, cloudops, deploy, provisioning, storage, outposts
  when_to_use: Invoke when the user wants to create S3 on Outposts — provisioning outpost buckets, endpoints (required for VPC access), access points, replication from Outpost to cloud S3, object lock (WORM), encryption (SSE-S3 only), lifecycle rules, or capacity management. Do NOT invoke for standard S3 (use s3 skills), S3 on Outposts rack (same skill applies), or FSx on Outposts (use fsx skills).
---

# S3 Outposts Deployer

An AWS CloudOps agent skill that provisions Amazon S3 on Outposts with
correct defaults. The skill walks the operator through outpost bucket
creation, endpoint requirements (mandatory VPC endpoint for access),
access point configuration, storage class constraints (STANDARD only),
encryption limitations (SSE-S3 only, no KMS), replication (one-way
from Outpost to cloud), object lock (WORM), lifecycle constraints, and
capacity management, captures outpost and networking decisions,
explains why each default matters, and emits a READY_TO_DEPLOY checklist
with copy-pasteable verification commands.

## Activation keywords

s3 outposts, s3 on outpost, outpost bucket, s3 outpost endpoint, s3
outpost access point, s3 outpost replication, object lock outpost, sse-s3
outpost, s3 outpost capacity.

## STRICT output contract

When this skill is invoked with an S3 on Outposts provisioning request
(create an outpost bucket, configure endpoint, set up access point,
enable replication, configure object lock, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`S3_OUTPOST:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[x]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — S3 on Outposts vs cloud S3 | Core differences |
| Step 2 — Endpoint (mandatory for access) | Networking |
| Step 3 — Bucket creation | Provisioning step |
| Step 4 — Access points (regional vs outpost) | Access management |
| Step 5 — Storage class (STANDARD only) | Storage constraints |
| Step 6 — Encryption (SSE-S3 only, no KMS) | Encryption |
| Step 7 — Versioning and lifecycle | Data management |
| Step 8 — Replication (Outpost to cloud, one-way) | DR/backup |
| Step 9 — Object lock (WORM) | Compliance |
| Step 10 — Capacity management and CloudWatch | Operations |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/endpoints-and-networking.md | Endpoint + networking detail |
| references/replication-and-capacity.md | Replication + capacity detail |

## Mindset

**One-line takeaway:** S3 on Outposts runs S3 storage on your physical
Outpost rack at your on-premises data center. It requires a VPC
endpoint for ALL access (no public API). Only STANDARD storage class
is supported (no IA, no Glacier). Encryption is SSE-S3 only (no KMS).
Replication from Outpost to cloud S3 is one-way. Outpost storage is
finite — capacity must be monitored.

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset-three-misconceptions-that-dominate-s3-on-outposts-misdesign) — cloud-S3 equivalence, public-internet access, KMS-on-Outposts.
Load that reference on demand before executing this section.

## Configuration dependency graph (novel heuristic)

S3 on Outposts configurations are NOT independent. The outpost must
exist. An endpoint must be created in a VPC before buckets can be
accessed. Access points must reference the endpoint. Replication
requires a destination cloud bucket. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Outpost rack | Outpost hardware installed and activated | must have S3 capacity allocated | outpost buckets |
| Endpoint | VPC + subnet on the Outpost; SecurityGroup | endpoint is required for ALL S3 API access to Outpost | bucket access |
| Bucket | Outpost ID; endpoint exists | bucket is created on the Outpost (not cloud) | objects, versioning, lifecycle |
| Access point | Bucket exists; endpoint exists | outpost access points are regional; regional access points route to outpost via endpoint | object-level access |
| Versioning | Bucket exists | once enabled, cannot be fully disabled (can suspend) | object versions |
| Lifecycle | Bucket exists | rules can only transition objects to Outpost S3 storage (STANDARD); NO cloud tier transitions | automated transitions |
| Replication | Source Outpost bucket exists; destination cloud S3 bucket exists | replication is ONE-WAY (Outpost → cloud); cannot replicate cloud → Outpost | cross-site replication |
| Object lock | Bucket created with object lock enabled at creation | object lock CANNOT be enabled after bucket creation; WORM is permanent | compliance retention |
| Encryption | Bucket exists | SSE-S3 only (no KMS on Outpost); encryption is enabled by default | data at rest |

**The endpoint-before-bucket-access row is the one a baseline model
misses.** Creating a bucket on the Outpost is not enough. Without the
S3 Outposts endpoint in a VPC, no client can access the bucket. The
endpoint is the networking bridge. The procedure below forces explicit
endpoint creation before bucket access is tested.

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#configuration-dependency-graph-cross-dependency-gotchas) — endpoint-VPC binding, AP resolution, object-lock-at-creation, one-way replication.
Load that reference on demand before executing this section.

## Expert heuristic: endpoint is the mandatory networking bridge

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-endpoint-is-the-mandatory-networking-bridge) — no-public-endpoint flow diagram and the VPC-connectivity implication.
Load that reference on demand before executing this section.

## Expert heuristic: one-way replication and capacity

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-one-way-replication-and-capacity) — replication direction matrix and finite-capacity management ladder.
Load that reference on demand before executing this section.

## Expert heuristic: object lock at creation only

Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-object-lock-at-creation-only) — creation-time requirement and the recovery path if you forgot.
Load that reference on demand before executing this section.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Outpost exists and is active | S3 capacity must be allocated on the Outpost | `aws outposts get-outpost --outpost-id op-xxx` |
| VPC with subnet on the Outpost | Endpoint must be in a VPC with Outpost connectivity | `aws ec2 describe-subnets --filters Name=outpost-arn,Values=...` |
| S3 capacity on Outpost confirmed | Outpost has finite storage; verify capacity | `aws outposts get-outpost-instance-types --outpost-id op-xxx` |
| Outpost ID known | Bucket creation requires Outpost ID | Confirm Outpost ARN |
| Security group for endpoint | Endpoint needs a security group for traffic | `aws ec2 describe-security-groups` |
| Destination cloud S3 bucket (if replication) | Replication target must exist | `aws s3 ls s3://cloud-destination-bucket` |
| Object lock decision (at creation) | Cannot be enabled later | Confirm WORM requirement |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — S3 on Outposts vs cloud S3

| Feature | Cloud S3 | S3 on Outposts |
|---|---|---|
| Location | AWS region | On-prem Outpost rack |
| Access | Public API + VPC endpoint | VPC endpoint ONLY (no public API) |
| Storage classes | STANDARD, IA, Glacier, etc. | STANDARD only |
| Encryption | SSE-S3, SSE-KMS, SSE-C | SSE-S3 only |
| Lifecycle transitions | Can transition to Glacier, Deep Archive | Can transition within Outpost STANDARD only |
| Replication | Bidirectional cross-region | One-way (Outpost to cloud) |
| KMS support | Yes (SSE-KMS) | NO |
| Capacity | Virtually unlimited | Finite (physical Outpost storage) |
| Public access | Configurable | Not available (endpoint only) |

**S3 on Outposts is for:** data residency requirements (data must stay
on-prem), ultra-low latency on-prem access, and hybrid cloud workflows
where data originates on-prem.

## Step 2 — Endpoint (mandatory for access)

The S3 Outposts endpoint is a VPC endpoint that routes S3 API traffic
from the VPC to the Outpost. Without it, the bucket is inaccessible.

Moved to [references/endpoints-and-networking.md](references/endpoints-and-networking.md#step-2-endpoint-creation-and-verification-moved-from-skillmd) — create-endpoint + list-endpoints CLI, Available-state requirement, security-group rules.
Load that reference on demand before executing this section.

## Step 3 — Bucket creation

Create the bucket on the Outpost:

Moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md#step-3-bucket-creation-moved-from-skillmd) — create-bucket (with/without object lock) and the Outposts ARN format.
Load that reference on demand before executing this section.

This ARN format is different from cloud S3 (`arn:aws:s3:::bucket-name`).
Outpost buckets use the `s3-outposts` service prefix and include the
outpost ID in the ARN.

## Step 4 — Access points (regional vs outpost)

Access points simplify access management for Outpost buckets. They
create a unique DNS name for the bucket.

Moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md#step-4-outpost-access-point-moved-from-skillmd) — create-access-point CLI and the outpost vs regional AP type table.
Load that reference on demand before executing this section.

Outpost access points are tied to the VPC where the endpoint exists.

## Step 5 — Storage class (STANDARD only)

S3 on Outposts supports ONLY the STANDARD storage class. There is no
STANDARD_IA, ONEZONE_IA, GLACIER, or DEEP_ARCHIVE.

```text
Cloud S3 classes:     STANDARD, STANDARD_IA, ONEZONE_IA, GLACIER, DEEP_ARCHIVE, etc.
S3 Outposts classes:  STANDARD (only)
```

**Implication:** you cannot archive data to Glacier on the Outpost.
For archival, replicate data to a cloud S3 bucket and apply lifecycle
rules there.

## Step 6 — Encryption (SSE-S3 only, no KMS)

S3 on Outposts supports SSE-S3 (Amazon S3 managed keys) only. SSE-KMS
is NOT available.

```text
Cloud S3 encryption:  SSE-S3, SSE-KMS, SSE-C, DSSE-KMS
S3 Outposts enc:      SSE-S3 (only)
```

**Implication:** if your compliance framework requires KMS-managed
keys for data at rest, S3 on Outposts alone does not satisfy that
requirement. You must replicate to cloud S3 with SSE-KMS enabled.

**SSE-S3 is enabled by default** on all Outpost S3 buckets. You do not
need to explicitly configure it.

## Step 7 — Versioning and lifecycle

### Versioning

Versioning works similarly to cloud S3:

```bash
aws s3control put-bucket-versioning \
  --account-id 123456789012 \
  --bucket "arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-xxx/bucket/my-outpost-bucket" \
  --versioning-configuration Status=Enabled
```

### Lifecycle rules

Lifecycle rules on Outpost S3 can ONLY transition objects within the
Outpost (STANDARD to STANDARD). They CANNOT transition to cloud
storage classes.

```text
Cloud S3 lifecycle:  STANDARD → IA → Glacier → Deep Archive
Outpost lifecycle:   STANDARD → STANDARD (expiration only)
```

**Lifecycle on Outpost is primarily for expiration** (deleting old
objects to free capacity). Use lifecycle rules to manage finite storage.

## Step 8 — Replication (Outpost to cloud, one-way)

Replication copies objects from the Outpost bucket to a cloud S3
bucket. This is ONE-WAY only — the cloud bucket cannot replicate back.

**Prerequisites:**
- Source: Outpost bucket
- Destination: cloud S3 bucket (in any region)
- Replication IAM role with read on source and write on destination

Moved to [references/replication-and-capacity.md](references/replication-and-capacity.md#step-8-replication-configuration-and-role-trust-policy-moved-from-skillmd) — put-bucket-replication JSON and the s3-outposts.amazonaws.com trust policy.
Load that reference on demand before executing this section.

**Key implication:** replication is the primary DR mechanism for
Outpost S3 data. The cloud bucket can have KMS encryption, lifecycle
rules (including Glacier), and cross-region replication — features not
available on the Outpost.

## Step 9 — Object lock (WORM)

Object lock enforces Write-Once-Read-Many (WORM) semantics. It MUST be
enabled at bucket creation.

**Two modes:**

| Mode | Description |
|---|---|
| COMPLIANCE | Object versions cannot be overwritten or deleted by ANY user (including root) for the retention period |
| GOVERNANCE | Object versions cannot be overwritten or deleted by most users; users with special permissions can bypass |

**Object lock is permanent** — once enabled, it cannot be disabled.

## Step 10 — Capacity management and CloudWatch

Outpost storage is finite. Monitor capacity to avoid write failures.

**CloudWatch metrics for S3 on Outposts:**

| Metric | Description |
|---|---|
| BucketSizeBytes | Total bytes used by the bucket |
| NumberOfObjects | Total objects in the bucket |
| BytesUploaded | Bytes uploaded in the period |
| BytesDownloaded | Bytes downloaded in the period |

Moved to [references/replication-and-capacity.md](references/replication-and-capacity.md#step-10-capacity-alarm-moved-from-skillmd) — CloudWatch put-metric-alarm on BucketSizeBytes at 80% threshold.
Load that reference on demand before executing this section.

**When capacity is full:**
- New PUT requests fail with `InsufficientStorageCapacity`
- Existing objects remain accessible
- Must free space via lifecycle expiration or replication + deletion

## NEVER do these things

1. **NEVER assume S3 on Outposts works like cloud S3.** It has strict
   constraints: STANDARD only, SSE-S3 only, no public API, endpoint
   required, one-way replication. Always account for these differences.

2. **NEVER try to access an Outpost bucket without an endpoint.** All
   access goes through the VPC endpoint. Without it, API calls fail.
   This is the #1 cause of access failures.

3. **NEVER expect KMS encryption on Outpost S3.** Only SSE-S3 is
   supported. For KMS, replicate to cloud S3.

4. **NEVER try to enable object lock after bucket creation.** Object
   lock MUST be enabled at creation time. If you need WORM and did not
   enable it, create a new bucket.

5. **NEVER expect bidirectional replication.** Replication is ONE-WAY
   (Outpost to cloud). Cloud-to-Outpost replication is not supported.

6. **NEVER create lifecycle rules expecting Glacier transitions.**
   Outpost lifecycle can only transition within STANDARD (expiration).
   Use cloud replication + cloud lifecycle for archival.

7. **NEVER ignore capacity monitoring.** Outpost storage is finite.
   When full, writes fail. Monitor via CloudWatch and use lifecycle
   rules to manage retention.

8. **NEVER use cloud S3 API calls for Outpost buckets.** Outpost
   buckets use `s3control` API (not `s3`). The ARN format is different
   (`s3-outposts` prefix, includes outpost ID).

9. **NEVER assume Outpost S3 has the same limits as cloud S3.** Bucket
   count, object count, and request rates may differ. Check Outpost-
   specific limits.

10. **NEVER forget the security group on the endpoint.** The endpoint
    security group controls which clients can access the Outpost S3.
    Without the correct inbound rules, access fails.

## Output format

```text
S3_OUTPOST: <bucket-name> on <outpost-id>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Outpost: <outpost-id> (<outpost-arn>) — ACTIVE
  [✓|✗] Endpoint: <endpoint-arn> — Available (subnet: <subnet-id>, SG: <sg-id>)
  [✓|✗] Bucket: <bucket-name> (<bucket-arn>)
  [✓|✗] Access point: <ap-name> (<ap-arn>) or "none"
  [✓|✗] Storage class: STANDARD (only class available)
  [✓|✗] Encryption: SSE-S3 (default, no KMS available)
  [✓|✗] Versioning: Enabled | Disabled
  [✓|✗] Lifecycle: <rules summary> or "none"
  [✓|✗] Replication: Outpost → cloud (<destination-bucket>) or "none"
  [✓|✗] Object lock: COMPLIANCE | GOVERNANCE | Disabled
  [✓|✗] Capacity alarm: <alarm-name> or "none"
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws s3control list-regional-buckets --account-id <account-id>
  aws s3outposts list-endpoints
  aws cloudwatch get-metric-statistics --namespace AWS/S3Outposts --metric-name BucketSizeBytes ...
```

### Worked example — outpost bucket with endpoint and replication

```text
S3_OUTPOST: my-outpost-bucket on op-0abc123def456
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Outpost: op-0abc123def456 — ACTIVE
  [✓] Endpoint: arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-0abc123def456/endpoint/abc-123 — Available (subnet: subnet-abc123, SG: sg-outpost-s3)
  [✓] Bucket: my-outpost-bucket (arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-0abc123def456/bucket/my-outpost-bucket)
  [✓] Access point: my-ap (regional)
  [✓] Storage class: STANDARD (only class available)
  [✓] Encryption: SSE-S3 (default)
  [✓] Versioning: Enabled
  [✓] Lifecycle: expiration after 90 days
  [✓] Replication: Outpost → cloud (s3://cloud-dr-bucket)
  [✓] Object lock: Disabled
  [✓] Capacity alarm: outpost-s3-capacity-80pct
  [✓] Tags: Environment=onprem, Application=data-lake
VERIFICATION_COMMANDS:
  aws s3control list-regional-buckets --account-id 123456789012
  aws s3outposts list-endpoints
  aws cloudwatch get-metric-statistics --namespace AWS/S3Outposts --metric-name BucketSizeBytes --dimensions Name=BucketName,Value=my-outpost-bucket --statistics Sum --period 300 --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T01:00:00Z
```

## Error handling

Moved to [references/error-handling.md](references/error-handling.md#error-handling) — deep dives: connection timeout, InsufficientStorageCapacity, KMS failure, object lock, replication.
Load that reference on demand before executing this section.


## References (load on demand)

- [references/endpoints-and-networking.md](references/endpoints-and-networking.md) — endpoint architecture, subnet/security-group requirements, VPC-vs-Outpost networking bridge, lifecycle, pitfalls, Terraform.
- [references/replication-and-capacity.md](references/replication-and-capacity.md) — one-way replication design, IAM roles, capacity monitoring/alarms, lifecycle constraints, Terraform.
- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — copy-pasteable CLI for bucket creation, access points, versioning, replication config, capacity alarm.
- [references/error-handling.md](references/error-handling.md) — error-handling deep dives (endpoint timeouts, InsufficientStorageCapacity, KMS, object lock, replication failures).
- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset misconceptions, cross-dependency gotchas, expert heuristics (endpoint bridge, one-way replication, object lock).
## Domain

AWS CloudOps / Amazon S3 on Outposts Provisioning & On-Premises Object
Storage Management.

## AWS documentation

- **S3 on Outposts** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/S3onOutposts.html
- **S3 Outposts endpoints** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Endpoint-S3onOutposts.html
- **S3 Outposts buckets** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/CreatingS3onOutpostsBucket.html
- **S3 Outposts access points** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/AccessPointsS3onOutposts.html
- **S3 Outposts replication** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/S3onOutpostsReplication.html
- **S3 Outposts object lock** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/S3onOutpostsObjectLock.html
- **s3control CLI** — https://docs.aws.amazon.com/cli/latest/reference/s3control/
- **s3outposts CLI** — https://docs.aws.amazon.com/cli/latest/reference/s3outposts/
