---
name: s3-directory-bucket-deployer
description: 'Provisions S3 Express One Zone directory buckets and S3 Tables table buckets with production defaults: directory bucket name format (base-name--az-id--x-s3), Availability Zone ID targeting, zone affinity for co-located compute (EC2/ECS/EKS in the same AZ for single-digit- millisecond latency), S3 Express One Zone pricing characteristics (lowest latency, highest requests/sec), table buckets for Apache Iceberg via S3 Tables, and the hard limitations (no cross-region replication, no versioning, no Object Lock, no Transfer Acceleration). Emits READY_TO_DEPLOY / PREREQUISITES_MISSING with every item verified and copy-pasteable s3api / s3tables / ec2 commands. Use when deploying S3 Express One Zone for latency-sensitive or high-throughput workloads. Triggers: S3 directory bucket, S3 Express One Zone, AZ ID bucket, table bucket, S3 Tables, zone-affinity compute, Iceberg on S3, directory bucket name format.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Live provisioning uses AWS CLI v2 with s3api (create-directory-bucket, get-bucket-location, list-buckets, get-bucket-encryption), s3tables (create-table-bucket, get-table-bucket), ec2 (describe-availability-zones, describe-subnets, run-instances), iam (create-role, attach-role-policy), and cloudformation / terraform aws_s3_directory_bucket equivalents.
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
  when_to_use: Creating an S3 Express One Zone directory bucket for latency- sensitive or high-throughput workloads, targeting a specific Availability Zone ID for zone affinity with co-located compute (EC2, ECS, EKS), deploying a table bucket for Apache Iceberg tables via S3 Tables, mapping AZ names to AZ IDs for directory bucket naming, or generating IaC (CloudFormation / Terraform) for any of the above. Do NOT invoke for general-purpose S3 buckets (use s3-secure-bucket-deployer), S3 on Outposts, or for cross-region replication requirements (directory buckets do not support CRR).
  activation_triggers: S3 directory bucket, S3 Express One Zone, directory bucket name format, AZ ID bucket, zone affinity compute, table bucket, S3 Tables, Apache Iceberg on S3, single-digit millisecond latency S3, directory bucket limitations
  invocation_schema: 'Input: either (a) a base bucket name + AZ ID (or AZ name to resolve) + optional encryption / compute placement spec, or (b) a table bucket spec for S3 Tables (Iceberg). Output: deterministic DIRECTORY_BUCKET_SPEC / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block per the STRICT output contract, where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: aws, s3, s3-express-one-zone, directory-bucket, az-id, zone-affinity, table-bucket, s3-tables, apache-iceberg, single-digit-latency, cloudops, deploy, storage
  tags: aws, s3, express-one-zone, directory-bucket, table-bucket, deploy, storage
  dependencies: aws-orchestrator
---

# S3 Directory Bucket Deployer

## What this skill does

Provisions S3 Express One Zone directory buckets and S3 Tables table
buckets with correct naming, zone placement, and compute co-location.
The skill walks an 8-step procedure, surfaces the silent-failure modes
unique to directory buckets (most dangerous: the directory bucket name
format is `base-name--az-id--x-s3` and any deviation silently creates a
standard bucket or fails; compute deployed in a different AZ pays
cross-AZ data-transfer fees and loses the latency benefit; table
buckets have a different API surface than general-purpose buckets and
standard S3 commands silently no-op), and emits a READY_TO_DEPLOY
checklist verifying every item against actual state. The single most
common incident this skill prevents: an operator creates a directory
bucket, deploys EC2 in the "same region," but a different AZ — the
latency profile looks like standard S3 and cross-AZ transfer charges
accumulate silently because the directory bucket's performance benefit
is only realized within its single AZ.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (8 steps), verdict thresholds, dependency graph | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Invocation contract** | Required literal labels in the response | Formatting the response |
| **Reasoning framework** | Why the 8-step order matters; AZ ID vs AZ name semantics | Understanding the deploy model |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "no latency benefit" |
| **Expert heuristic** | The zone-mismatch trap; name format parsing; table bucket API divergence | Pre-empt production incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **8-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent silent exposure / data-plane bugs | Review before deploy |
| **STRICT output contract** | Required DIRECTORY_BUCKET_SPEC / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | S3 Tables integration, AZ ID targeting, zone-optimized compute | Stay current |

## Quick reference — provisioning summary (8 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Resolve AZ ID from AZ name (or accept explicit AZ ID) | — | Wrong AZ → cross-AZ latency + transfer fees |
| 2 | Construct directory bucket name in `base--az-id--x-s3` format | — | **Wrong format → creation fails or creates wrong bucket type** |
| 3 | Create the directory bucket with `create-directory-bucket` | Yes | Using `create-bucket` instead → creates a standard bucket silently |
| 4 | Configure encryption (SSE-S3 or SSE-KMS) and bucket policy | Yes | directory bucket policy format differs from standard bucket policy |
| 5 | Deploy or confirm zone-affinity compute in the SAME AZ | Yes | **Compute in different AZ → no latency benefit + cross-AZ transfer fees** |
| 6 | For table buckets: create via `s3tables create-table-bucket` | Yes | Using `create-directory-bucket` for a table bucket → wrong API surface |
| 7 | Configure application to use the Zonal endpoint | — | Standard regional endpoint → routing overhead, loses latency benefit |
| 8 | Verify every configuration item against actual state + emit checklist | — | silent no-ops |

**Critical ordering constraints:** AZ ID resolution BEFORE bucket name
construction (the name encodes the AZ); bucket name format validation
BEFORE `create-directory-bucket` (the API rejects malformed names but
operators who use `create-bucket` get a standard bucket with no error);
directory bucket creation BEFORE compute deployment (compute should
target the bucket's AZ); table bucket creation uses a separate API
(`s3tables`, not `s3api`). Rationale and the silent-failure table are
below.

## Activation keywords

S3 directory bucket, S3 Express One Zone, directory bucket name format,
AZ ID, Availability Zone ID, zone affinity, zone-optimized compute,
table bucket, S3 Tables, Apache Iceberg on S3, single-digit millisecond
latency S3, directory bucket limitations, create-directory-bucket,
base-name--az-id--x-s3, Zonal endpoint, S3 Express One Zone pricing,
directory bucket no CRR, directory bucket no versioning.

## Invocation contract (hard requirement)

When this skill is invoked with an S3 directory bucket or table bucket
provisioning request, the agent MUST respond with the checklist defined
in §"STRICT output contract" using the literal all-caps labels
`DIRECTORY_BUCKET_SPEC:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

## Reasoning framework (why the provisioning order matters)

S3 Express One Zone directory buckets look like "a faster S3 bucket."
The underlying model has four traps:

1. **The bucket name IS the AZ selector.** Directory bucket names
   follow the rigid format `base-name--az-id--x-s3` (double-dash
   delimited). The `az-id` segment (e.g., `use1-az1`) is the
   Availability Zone ID, not the AZ name (`us-east-1a`). Operators who
   use the AZ name or omit the `--x-s3` suffix get a creation error or,
   worse, fall back to `create-bucket` and silently create a standard
   general-purpose bucket with none of the Express One Zone benefits.

2. **Zone affinity is the entire value proposition.** A directory
   bucket exists in exactly one AZ. Compute in the same AZ gets
   single-digit-millisecond latency and the highest requests-per-second
   throughput. Compute in a different AZ of the same region pays
   cross-AZ data-transfer fees ($0.01/GB in each direction) and loses
   the latency advantage — the workload performs no better than
   standard S3 but costs more per request.

3. **Table buckets use a separate API.** S3 Tables table buckets (for
   Apache Iceberg) are a specialized directory bucket type created via
   `aws s3tables create-table-bucket`, not `aws s3api
   create-directory-bucket`. Operators who use the wrong API either get
   a plain directory bucket (no table semantics) or an error.

4. **The limitations are hard, not soft.** Directory buckets do not
   support cross-region replication, versioning, Object Lock, Transfer
   Acceleration, or cross-Region endpoints. An operator who assumes
   these "just work" discovers the gap when a compliance audit fails
   or a DR runbook produces an empty bucket.

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing) | Enables downstream |
|---|---|---|---|
| Directory bucket name format | AZ ID resolved; `--x-s3` suffix | **operator falls back to `create-bucket` → standard bucket created, no error, no Express benefit** | correct bucket type |
| `create-directory-bucket` API | name format valid; AZ ID exists | **operator uses `create-bucket` → general-purpose bucket silently, no Express One Zone performance** | Express One Zone tier |
| Zone-affinity compute | EC2/ECS/EKS in same AZ as bucket | **compute in different AZ → cross-AZ transfer fees + no latency benefit; no error surfaced** | single-digit-ms latency |
| Zonal endpoint | directory bucket exists | **client uses regional endpoint → request routes through regional S3, adds latency overhead; no error** | optimal routing |
| Table bucket (S3 Tables) | `s3tables` API; Iceberg format | **operator uses `create-directory-bucket` → plain directory bucket, no table semantics; or `create-bucket` → standard bucket** | Iceberg table operations |
| Bucket encryption | directory bucket exists | **SSE-KMS key in wrong region → creation fails; SSE-S3 is default but some compliance requires SSE-KMS** | encryption compliance |
| Bucket policy | directory bucket exists; Zonal endpoint ARN format | **policy uses standard bucket ARN format → matches nothing; AccessDenied regardless of intent** | client scoping |
| Cross-region replication | NOT SUPPORTED | **operator configures CRR → API silently ignores or errors with unclear message; DR gap** | N/A — use app-level replication |

**The four silent-failure rows are the ones a baseline model misses.**
Wrong API (`create-bucket` instead of `create-directory-bucket`), zone
mismatch, regional endpoint routing, and wrong policy ARN format all
produce successful-looking operations with no Express One Zone benefit.
This is why the procedure verifies every item rather than trusting the
API response.

## Expert heuristic: the zone-mismatch trap

The most dangerous directory bucket misconfiguration: compute in a
different AZ than the bucket.

```text
Operator thinks:              What actually happens:
"Same region" is enough  →   The directory bucket is in exactly one AZ;
                               EC2 in a different AZ of the same region
                               pays $0.01/GB cross-AZ transfer each way
                               and sees ~10x higher latency than zone-
                               affinity placement. No error is surfaced;
                               the workload just costs more and runs
                               slower with no signal.
```

The tell-tale signal: S3 request latency is 10-50ms instead of
single-digit milliseconds, and Cost Explorer shows Data Transfer -
Regional line items between EC2 and S3 in the same region. Remedy:
pin compute to the directory bucket's AZ using subnet AZ filtering
or an EC2 Capacity Reservation in that AZ; verify with a latency
probe (`time aws s3 ls s3://<bucket> --region <region>`).

## Expert heuristic: the name format parser

Directory bucket names have a rigid structure that encodes the AZ:

```text
  my-app-data--use1-az1--x-s3
  ^^^^^^^^^^^   ^^^^^^^^ ^^^^^
  base name     AZ ID    mandatory suffix
```

Rules a baseline model misses:

1. **Double-dash (`--`) is the delimiter, not single dash.** A base
   name containing `--` collides with the parser and is rejected.

2. **The AZ ID is NOT the AZ name.** `use1-az1` maps to `us-east-1a`
   but the mapping is account-specific (AZ `us-east-1a` for account A
   may map to `use1-az4` for account B). Always resolve with
   `ec2 describe-availability-zones --zone-names us-east-1a`.

3. **The `--x-s3` suffix is mandatory.** Without it, the API rejects
   the name. Operators who drop the suffix and switch to `create-bucket`
   silently create a general-purpose bucket.

4. **The base name must be DNS-compatible and globally unique within
   the AZ.** Directory bucket names are not globally unique across all
   AWS like standard buckets, but they must be unique within the AZ.

## Expert heuristic: table bucket API divergence

S3 Tables table buckets are a directory bucket type for Apache Iceberg
tables. The API surface is `aws s3tables`, not `aws s3api`:

```bash
# WRONG — plain directory bucket, no table semantics
aws s3api create-directory-bucket --bucket my-iceberg--use1-az1--x-s3 ...

# CORRECT — table bucket via the S3 Tables API
aws s3tables create-table-bucket \
  --name my-iceberg-tables \
  --region use1-az1
```

The `--region` parameter for `create-table-bucket` takes the AZ ID
(e.g., `use1-az1`), not a standard region string. Table buckets
support table-level operations (`create-table`, `get-table`,
`put-table-data`), not object-level operations. Operators who try to
`PutObject` into a table bucket get an error because the API surface is
fundamentally different.

## Prerequisites (verify before provisioning)

Before emitting any provisioning command, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AZ ID resolved (or AZ name available to resolve) | The bucket name encodes the AZ ID; wrong AZ = no benefit | `aws ec2 describe-availability-zones --zone-names <AZ_NAME> --query 'AvailabilityZones[0].ZoneId'` |
| Base bucket name (no double-dash) | Double-dash in base name collides with the format parser | manual validation |
| Region supports S3 Express One Zone | Not all regions support Express One Zone | `aws s3api list-buckets --region <REGION>` (no error) |
| Compute placement plan (same AZ) | Zone affinity is the entire value proposition | `aws ec2 describe-subnets --filters Name=availability-zone-id,Values=<AZ_ID>` |
| KMS key in same region (if SSE-KMS) | SSE-KMS requires a key in the same region as the bucket | `aws kms list-aliases --region <REGION>` |
| Account ID | Required for bucket policy ARN construction | `aws sts get-caller-identity --query Account --output text` |
| No unsupported feature requirement | CRR, versioning, Object Lock are NOT supported | requirements review |
| Table bucket vs directory bucket decision | Table buckets use a different API surface | workload type (Iceberg = table bucket) |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 8-step provisioning procedure

### Step 1 — Resolve the AZ ID

The AZ ID (`use1-az1`) is account-specific and differs from the AZ name
(`us-east-1a`). Always resolve from the AZ name unless the operator
provides an explicit AZ ID.

```bash
# Resolve AZ ID from AZ name
aws ec2 describe-availability-zones \
  --zone-names us-east-1a \
  --query 'AvailabilityZones[0].[ZoneName,ZoneId]' --output text
# Output: us-east-1a   use1-az1

# List all AZs in a region to pick the target
aws ec2 describe-availability-zones \
  --region us-east-1 \
  --query 'AvailabilityZones[].[ZoneName,ZoneId]' --output table
```

**Common mistake:** assuming `us-east-1a` always maps to `use1-az1`.
The AZ-name-to-AZ-ID mapping is consistent within an account but varies
across accounts. Always resolve programmatically.

### Step 2 — Construct the directory bucket name

Assemble the name in the rigid `base-name--az-id--x-s3` format.

```bash
BASE_NAME="my-app-data"
AZ_ID="use1-az1"
DIRECTORY_BUCKET="${BASE_NAME}--${AZ_ID}--x-s3"
echo "$DIRECTORY_BUCKET"
# my-app-data--use1-az1--x-s3
```

Validation checklist for the name:
- Base name contains NO double-dash (`--`)
- Base name is DNS-compatible (lowercase, alphanumeric, hyphens only)
- AZ ID is in the `xxxx-azN` format (e.g., `use1-az1`, `apne1-az2`)
- Suffix is exactly `--x-s3`
- Total name length is within S3 bucket name limits

**Common mistake:** using a single dash (`-`) as the delimiter. The
API rejects single-dash names; operators who switch to `create-bucket`
get a standard bucket with no error.

### Step 3 — Create the directory bucket

```bash
# S3 Express One Zone directory bucket
aws s3api create-directory-bucket \
  --bucket my-app-data--use1-az1--x-s3 \
  --data-redundancy SingleAvailabilityZone \
  --region us-east-1
```

**Common mistake:** using `aws s3api create-bucket`. This creates a
general-purpose S3 bucket (standard tier) with NO Express One Zone
benefits. The operation succeeds silently. Always verify the bucket
type after creation with `list-buckets --output json` and check for the
`BucketType: Directory` field.

### Step 4 — Configure encryption and bucket policy

```bash
# Default encryption (SSE-KMS)
aws s3api put-bucket-encryption \
  --bucket my-app-data--use1-az1--x-s3 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:111111111111:key/<KEY_ID>"
      }
    }]
  }'
```

The bucket policy for a directory bucket uses the Zonal endpoint ARN
format (`arn:aws:s3express:<region>:<account>:<bucket>`), NOT the
standard S3 ARN format:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::<ACCOUNT>:role/<APP_ROLE>"},
    "Action": ["s3express:GetObject", "s3express:PutObject", "s3express:ListBucket"],
    "Resource": [
      "arn:aws:s3express:<REGION>:<ACCOUNT>:<BUCKET>",
      "arn:aws:s3express:<REGION>:<ACCOUNT>:<BUCKET>/*"
    ]
  }]
}
```

**Common mistake:** using `arn:aws:s3:::<bucket>` (standard ARN) in the
policy. The policy matches nothing and clients get AccessDenied
regardless of intent. Directory buckets use the `s3express` service
prefix and Zonal endpoint ARNs.

### Step 5 — Deploy or confirm zone-affinity compute

Pin compute to the same AZ as the directory bucket.

```bash
# Find subnets in the target AZ
aws ec2 describe-subnets \
  --filters Name=availability-zone-id,Values=use1-az1 \
  --query 'Subnets[].[SubnetId,AvailabilityZoneId]' --output table

# Launch EC2 in the same AZ
aws ec2 run-instances \
  --image-id ami-<AMI_ID> \
  --instance-type c7n.large \
  --subnet-id subnet-<SUBNET_IN_AZ> \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=zone-affinity-app}]"
```

For ECS/EKS, set the `availabilityZone` constraint on the node group or
task placement to match the directory bucket's AZ. For an EC2 Auto
Scaling Group, restrict subnets to the target AZ.

**Common mistake:** deploying compute "in the same region" without
checking the AZ. The directory bucket exists in exactly one AZ; compute
in any other AZ pays cross-AZ transfer fees and sees no latency benefit.

### Step 6 — For table buckets: create via S3 Tables API

```bash
# S3 Tables table bucket for Apache Iceberg
aws s3tables create-table-bucket \
  --name analytics-iceberg-tables \
  --region use1-az1

# Create an Iceberg table inside the table bucket
aws s3tables create-table \
  --table-bucket-name analytics-iceberg-tables \
  --name events_iceberg \
  --format ICEBERG \
  --metadata '{"format-version":"2","write.ordering":"event_ts"}'
```

Table buckets do NOT support object-level operations (`PutObject`,
`GetObject`). They support table-level operations via the `s3tables`
API and integrations with Athena, Glue, Spark, and Trino for Iceberg
table access.

**Common mistake:** trying to use `aws s3api put-object` on a table
bucket. The operation fails because table buckets have a fundamentally
different API surface.

### Step 7 — Configure application for Zonal endpoint

Directory buckets are accessed via Zonal endpoints, not regional
endpoints. The AWS SDK and CLI auto-route when using the bucket name,
but verify the endpoint:

```bash
# Verify the Zonal endpoint
aws s3api get-bucket-location \
  --bucket my-app-data--use1-az1--x-s3

# Quick latency probe (should be single-digit ms from same-AZ compute)
time aws s3 ls s3://my-app-data--use1-az1--x-s3/ --region us-east-1
```

For application code using the SDK, ensure the S3 client does not
override the endpoint to a regional endpoint. The SDK resolves the
Zonal endpoint from the bucket name format automatically.

### Step 8 — Verification

Run every verification command and confirm each output matches the
expected state.

```bash
# Verify bucket type is Directory (not general-purpose)
aws s3api list-buckets --query 'Buckets[?Name==`my-app-data--use1-az1--x-s3`]' --output json

# Verify encryption
aws s3api get-bucket-encryption --bucket my-app-data--use1-az1--x-s3

# Verify bucket policy
aws s3api get-bucket-policy --bucket my-app-data--use1-az1--x-s3

# Verify compute is in the same AZ
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=zone-affinity-app" \
  --query 'Reservations[].Instances[].[InstanceId,Placement.AvailabilityZone,Placement.AvailabilityZoneId]' \
  --output table

# For table buckets: verify table exists
aws s3tables list-tables --table-bucket-name analytics-iceberg-tables

# Latency probe (from zone-affinity compute, should be single-digit ms)
time aws s3 ls s3://my-app-data--use1-az1--x-s3/ --region us-east-1
```

## NEVER do these things

These anti-patterns cause silent performance loss, cost overruns, or
compliance gaps. Each is observed in real production incidents — the
"why it's wrong" line is the post-mortem finding.

1. **NEVER use `create-bucket` to create a directory bucket.** Why it's
   wrong: `create-bucket` creates a general-purpose S3 bucket in the
   standard tier with NO Express One Zone benefits. The operation
   succeeds silently. Always use `create-directory-bucket` with
   `--data-redundancy SingleAvailabilityZone` and verify the
   `BucketType: Directory` field after creation.

2. **NEVER deploy compute in a different AZ than the directory bucket.**
   Why it's wrong: a directory bucket exists in exactly one AZ. Compute
   in any other AZ pays cross-AZ data-transfer fees ($0.01/GB each way)
   and sees 10x higher latency with no error surfaced. Pin compute to
   the bucket's AZ using subnet filtering or capacity reservations.

3. **NEVER use a standard S3 ARN (`arn:aws:s3:::`) in a directory
   bucket policy.** Why it's wrong: directory buckets use the
   `s3express` service prefix and Zonal endpoint ARNs
   (`arn:aws:s3express:<region>:<account>:<bucket>`). A standard ARN
   matches nothing and clients get AccessDenied regardless of intent.

4. **NEVER assume directory buckets support standard S3 features.** Why
   it's wrong: directory buckets do NOT support cross-region replication,
   versioning, Object Lock, Transfer Acceleration, or cross-Region
   endpoints. An operator who configures CRR discovers the gap during a
   DR runbook. Verify the workload's requirements against the limitations
   list BEFORE provisioning.

5. **NEVER use `create-directory-bucket` for an S3 Tables table bucket.**
   Why it's wrong: table buckets are created via `aws s3tables
   create-table-bucket`, a separate API. Using `create-directory-bucket`
   creates a plain directory bucket with no table semantics. The Iceberg
   table operations will fail.

## Output format

```
DIRECTORY_BUCKET_SPEC: <bucket-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] AZ ID resolved: <az-id> (from AZ name <az-name>)
  [✓|✗] Directory bucket name format: base--az-id--x-s3 verified
  [✓|✗] Directory bucket created: BucketType=Directory confirmed
  [✓|✗] Encryption: SSE-S3 | SSE-KMS (<key-id>)
  [✓|✗] Bucket policy: s3express ARN format, correct principal
  [✓|✗] Zone-affinity compute: <n> instances in AZ <az-id>
  [✓|✗] Table bucket (if applicable): created via s3tables API | N/A
  [✓|✗] Unsupported features confirmed absent: CRR=no, versioning=no, Object Lock=no
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks complete but contains a silent misconfiguration.
Self-check EVERY emitted block against these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT preface with prose, headings, or disclaimers.

```text
DIRECTORY_BUCKET_SPEC: <bucket-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] AZ ID resolved: <az-id> (from AZ name <az-name>)
  [✓|✗] Directory bucket name format: base--az-id--x-s3 verified
  [✓|✗] Directory bucket created: BucketType=Directory confirmed
  [✓|✗] Encryption: SSE-S3 | SSE-KMS (<key-id>)
  [✓|✗] Bucket policy: s3express ARN format, correct principal
  [✓|✗] Zone-affinity compute: <n> instances in AZ <az-id>
  [✓|✗] Table bucket (if applicable): created via s3tables API | N/A
  [✓|✗] Unsupported features confirmed absent: CRR=no, versioning=no, Object Lock=no
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 8
   checklist items.** Every item MUST appear with a status marker:
   `[✓]` (applied and verified), `[✗]` (not applied or misconfigured),
   or `[N/A]` (not needed for this workload). Omitting a row implies it
   was not evaluated.

2. **NEVER mark the directory bucket name format as `[✓]` without
   showing the full bucket name.** The name encodes the AZ and the
   `--x-s3` suffix. A bare `[✓]` with no name implies the format was
   not validated. The full name MUST be cited.

3. **NEVER mark the directory bucket creation as `[✓]` without
   confirming `BucketType: Directory`.** Operators who use
   `create-bucket` get a standard bucket. The verification MUST cite
   the `BucketType` field from `list-buckets`.

4. **NEVER mark zone-affinity compute as `[✓]` without citing the
   specific AZ ID.** A bare `[✓]` implies "same region" which is
   insufficient. The AZ ID of the compute MUST match the bucket's AZ ID.

5. **NEVER mark table bucket as `[✓]` without confirming the `s3tables`
   API was used.** Using `create-directory-bucket` for a table bucket
   produces a plain directory bucket. The verification MUST cite the
   `s3tables` command.

6. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] AZ ID not resolved — operator must provide AZ name or AZ ID`.
   A bare `[✗]` with no explanation is non-compliant.

### Perfect example output — READY_TO_DEPLOY

```text
DIRECTORY_BUCKET_SPEC: my-app-data--use1-az1--x-s3
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] AZ ID resolved: use1-az1 (from AZ name us-east-1a)
  [✓] Directory bucket name format: my-app-data--use1-az1--x-s3 verified (double-dash delimited, --x-s3 suffix)
  [✓] Directory bucket created: BucketType=Directory confirmed via list-buckets
  [✓] Encryption: SSE-KMS (arn:aws:kms:us-east-1:111111111111:key/abc-123)
  [✓] Bucket policy: s3express ARN format (arn:aws:s3express:us-east-1:111111111111:my-app-data--use1-az1--x-s3)
  [✓] Zone-affinity compute: 4 x c7n.large in AZ use1-az1 (subnet subnet-aaa)
  [N/A] Table bucket: not applicable (object-level workload)
  [✓] Unsupported features confirmed absent: CRR=no, versioning=no, Object Lock=no
VERIFICATION_COMMANDS:
  aws ec2 describe-availability-zones --zone-names us-east-1a --query 'AvailabilityZones[0].[ZoneName,ZoneId]' --output text
  aws s3api list-buckets --query 'Buckets[?Name==`my-app-data--use1-az1--x-s3`]' --output json
  aws s3api get-bucket-encryption --bucket my-app-data--use1-az1--x-s3
  aws s3api get-bucket-policy --bucket my-app-data--use1-az1--x-s3
  aws ec2 describe-instances --filters "Name=tag:Name,Values=zone-affinity-app" --query 'Reservations[].Instances[].[InstanceId,Placement.AvailabilityZoneId]' --output table
```

### Perfect example output — PREREQUISITES_MISSING

```text
DIRECTORY_BUCKET_SPEC: my-app-data--use1-az1--x-s3
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] AZ ID resolved: use1-az1 (from AZ name us-east-1a)
  [✓] Directory bucket name format: my-app-data--use1-az1--x-s3 verified
  [✗] Directory bucket created: not yet created — run create-directory-bucket with --data-redundancy SingleAvailabilityZone
  [✗] Encryption: not configured — specify SSE-S3 or SSE-KMS key
  [✗] Bucket policy: not configured — use s3express ARN format
  [✗] Zone-affinity compute: EC2 deployed in use1-az2, NOT use1-az1 — relocate compute to bucket's AZ
  [N/A] Table bucket: not applicable
  [✗] Unsupported features: operator requested CRR — directory buckets do NOT support cross-region replication
VERIFICATION_COMMANDS:
  aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,Placement.AvailabilityZoneId]' --output table
  aws s3api list-buckets --query 'Buckets[?Name==`my-app-data--use1-az1--x-s3`]' --output json
```

**Self-check before emit:**
- [ ] All 8 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] Directory bucket name shows the full `base--az-id--x-s3` format?
- [ ] Bucket creation verification cites `BucketType: Directory`?
- [ ] Zone-affinity compute cites the specific AZ ID matching the bucket?
- [ ] Table bucket (if applicable) cites the `s3tables` API?
- [ ] Unsupported features (CRR, versioning, Object Lock) confirmed absent?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

## Recent AWS features

- **S3 Tables (table buckets)**: S3 Tables provides fully managed Apache
  Iceberg table storage in directory buckets. Created via `aws s3tables
  create-table-bucket` with the AZ ID as the region parameter. Table
  buckets support table-level operations and integrate with Athena,
  Glue, Spark, and Trino for analytics workloads. They do NOT support
  object-level operations (`PutObject`/`GetObject`).

- **AZ ID targeting for directory buckets**: directory buckets encode
  the AZ ID directly in the bucket name (`base--az-id--x-s3`), allowing
  precise single-AZ placement. The AZ ID is account-specific and must
  be resolved from the AZ name via `ec2 describe-availability-zones`.

- **Zone-optimized compute placement**: EC2, ECS, and EKS support
  Availability Zone ID targeting for co-locating compute with directory
  buckets. Use subnet AZ filtering or capacity reservations to pin
  compute to the directory bucket's AZ. This is the key configuration
  that delivers the single-digit-millisecond latency and highest
  requests-per-second throughput.

- **S3 Express One Zone pricing**: Express One Zone has the lowest
  latency and highest requests-per-second of any S3 tier. Pricing
  includes charges for PUT/POST/LIST requests, GET/SELECT requests,
  data retrieval, and storage. Data transfer between a directory bucket
  and compute in the same AZ is free; cross-AZ transfer incurs standard
  regional data-transfer fees.

- **Zonal endpoint auto-routing**: the AWS SDK and CLI auto-resolve the
  Zonal endpoint from the directory bucket name format. Applications
  should NOT override the endpoint to a regional endpoint — doing so
  adds routing overhead and negates the latency benefit.

- **SSE-KMS support**: directory buckets support both SSE-S3 (default)
  and SSE-KMS with a customer-managed key. The KMS key must be in the
  same region as the directory bucket.
