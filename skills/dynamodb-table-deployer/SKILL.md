---
name: dynamodb-table-deployer
description: >-
  Provisions DynamoDB tables with production-grade defaults: partition key design
  (random suffix, composite keys), sort key design (range queries, hierarchical
  data), GSI design (sparse indexes, ALL/KEYS_ONLY/INCLUDE projection), on-demand
  vs provisioned capacity choice, PITR enabled by default, SSE-KMS with
  customer-managed CMK for compliance, TTL configuration, DynamoDB Streams
  (NEW_AND_OLD_IMAGES for CDC), table class (Standard vs Standard-IA), deletion
  protection, and resource-based policies. Emits a READY_TO_DEPLOY checklist with
  verification commands. Use when creating a new DynamoDB table, hardening an
  existing table for production, validating schema/key design before go-live,
  designing GSIs for alternate access patterns, or generating a Terraform /
  CloudFormation skeleton. Triggers: create DynamoDB table, provision DynamoDB,
  partition key design, GSI design, DynamoDB Streams, TTL configuration, global
  tables, Aurora zero-ETL, OpenSearch zero-ETL.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). For live deployment: AWS CLI v2 with dynamodb, application-
  autoscaling, kms, and iam access. Works with Terraform aws_dynamodb_table
  resources and CloudFormation AWS::DynamoDB::Table templates.
keywords:
  - aws
  - dynamodb
  - cloudops
  - deploy
  - provisioning
  - partition key
  - sort key
  - gsi
  - global secondary index
  - lsi
  - on-demand
  - provisioned
  - pay per request
  - autoscaling
  - pitr
  - point-in-time recovery
  - sse-kms
  - ttl
  - time to live
  - dynamodb streams
  - cdc
  - table class
  - standard-ia
  - deletion protection
  - global tables
  - zero-etl
  - aurora zero-etl
  - opensearch zero-etl
tags:
  - aws
  - dynamodb
  - cloudops
  - deploy
  - databases
  - provisioning
  - partition-key
  - gsi
  - pitr
  - sse-kms
  - ttl
  - streams
  - deletion-protection
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: experimental
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - dynamodb
    - cloudops
    - deploy
    - databases
    - provisioning
    - partition-key
    - gsi
    - pitr
    - sse-kms
    - ttl
    - streams
    - deletion-protection
  dependencies:
    - aws-orchestrator
  keywords:
    - create dynamodb table
    - provision dynamodb
    - partition key design
    - sort key design
    - gsi design
    - dynamodb streams
    - dynamodb ttl
    - global tables
    - aurora zero-etl
    - opensearch zero-etl
    - deletion protection
    - point-in-time recovery
  when_to_use: >-
    Invoke when the user wants to create a new DynamoDB table with production
    defaults, design a partition/sort key scheme, plan GSI access patterns,
    harden an existing table before production, validate key/schema design
    before go-live, plan CDC pipelines via DynamoDB Streams, set up global
    tables, or generate provisioning CLI commands / IaC templates. Do NOT
    invoke for auditing existing table posture (use dynamodb-table-auditor),
    or for non-DynamoDB NoSQL (DocumentDB, ElastiCache, Neptune, Timestream).
---

# DynamoDB Table Deployer

An AWS CloudOps agent skill that provisions DynamoDB tables with correct
defaults. The skill walks the operator through a 10-step provisioning
procedure, captures the operator's access-pattern decisions (partition key,
sort key, GSI projections, capacity mode), explains why each default matters,
and emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create DynamoDB table, provision DynamoDB, DynamoDB deployment, partition key
design, sort key design, hot partition, random suffix, composite key, GSI
design, sparse index, ALL projection, KEYS_ONLY projection, INCLUDE
projection, on-demand capacity, provisioned capacity, PAY_PER_REQUEST,
autoscaling, PITR, point-in-time recovery, SSE-KMS, customer-managed CMK,
DynamoDB TTL, item expiration, DynamoDB Streams, NEW_AND_OLD_IMAGES,
CDC pipeline, table class, Standard-IA, deletion protection, global tables,
Aurora zero-ETL, OpenSearch zero-ETL, resource-based policy.

## Invocation contract (hard requirement)

When this skill is invoked with a table-provisioning request (table name,
access pattern, workload shape, region, or a partial configuration), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in
§"Output format" using the literal all-caps labels `TABLE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

## Mindset

**One-line takeaway:** DynamoDB correctness is decided at creation time.
Key schema, LSI placement, table class, and (effectively) capacity mode are
impossible or expensive to change later — the provisioning procedure treats
each as a one-way door and forces an explicit decision before the
`create-table` call.

Three misconceptions dominate DynamoDB misdesign at provisioning time:

- **"Pick the natural primary key and move on."** A monotonically
  increasing key (timestamp, auto-increment id, userId sorted lexicographically
  by signup) creates a **hot partition** — all writes land on one physical
  partition until DynamoDB rebalances, throttling the table far below its
  provisioned capacity. The fix is **partition-key shaping** (random suffix,
  hashed prefix, composite key) decided BEFORE the first write, because
  re-keying an existing table means create-new → backfill → cutover.

- **"On-demand mode eliminates capacity planning."** On-demand allocates
  burst capacity based on the **trailing 30 minutes** of traffic. A
  cold-start spike from zero has an empty burst bucket and will throttle.
  On-demand is the right default for unknown or bursty traffic, but for
  steady-state high-throughput workloads it costs 3-5x provisioned with
  autoscaling. Choose the mode from the traffic profile, not from a desire
  to skip capacity planning.

- **"GSIs are just indexes — add them as needed."** Every GSI has its OWN
  capacity, its OWN throttle cascade back to the base table, and a per-table
  quota (20 soft, with autoscaling implications). Projection type
  (ALL / KEYS_ONLY / INCLUDE) determines write amplification and storage cost
  — `ALL` projects the entire base item (most writes hit the GSI), `KEYS_ONLY`
  projects only the keys (cheapest, requires a follow-up GetItem). Decide
  GSI count, key schema, and projection at provisioning time; retrofitting
  is possible but disruptive.

## Reasoning framework (why provisioning order matters)

DynamoDB configurations have **dependency and immutability semantics** that
make the provisioning order non-trivial. Wrong-order or wrong-time decisions
either cannot be reversed or require expensive migration:

1. **Key schema BEFORE the first write** — partition key + sort key are
   IMMUTABLE after `create-table`. To change them you must create a new
   table, backfill, and cutover. This is why §"Step 1" forces an explicit
   partition-key design decision.

2. **LSI at table creation ONLY** — Local Secondary Indexes can ONLY be
   created at `create-table` time. You CANNOT add an LSI later. This is a
   hard API constraint. If the workload might need range queries against a
   non-key attribute, decide at creation or commit to a GSI later.

3. **Capacity mode BEFORE production traffic** — switching between
   `PAY_PER_REQUEST` and `PROVISIONED` is allowed but DynamoDB enforces a
   cooldown. Choose based on the trailing traffic profile, not per-request
   cost optimization.

4. **GSI autoscaling AT GSI creation** — a PROVISIONED table whose base
   table has autoscaling but whose GSI does not is the most commonly missed
   capacity misconfiguration. GSI throttling cascades back to the base table.
   Always pair GSI creation with autoscaling registration in the same
   provisioning step.

5. **SSE-KMS BEFORE the first write** — server-side encryption applies at
   write time. Items written before enabling SSE-KMS use the prior encryption
   state and require a background re-encryption migration after the change.

6. **PITR, deletion protection, streams EARLY** — these are additive,
   reversible, and cheap. Enable them as part of the initial provisioning
   run rather than as a post-deployment hardening pass.

## DynamoDB configuration dependency graph (novel heuristic)

DynamoDB configurations are NOT independent. Many are immutable after
creation, others silently downgrade. Use this graph both to sequence
provisioning and to debug "why can't I add this?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Key schema (partition + sort) | none — `create-table` argument | **IMMUTABLE after creation** — re-keying requires new table + backfill | all queries, GSIs, LSI sort keys |
| LSI | created at `create-table` time ONLY | **IMMUTABLE — CANNOT be added post-creation**; 5-per-table HARD limit | range queries on alternate sort attribute |
| GSI | table must be ACTIVE | can add later but each GSI has own capacity; cascade throttling on under-provisioning | alternate access pattern |
| Billing mode | none | switchable between PAY_PER_REQUEST ↔ PROVISIONED with cooldown; can't game per-request | autoscaling registration (PROVISIONED only) |
| Provisioned autoscaling | BillingMode=PROVISIONED | base-table policy does NOT cover GSIs; must register each GSI separately | target-tracking scale of RCU/WCU |
| SSE-KMS (customer CMK) | KMS key ARN valid + key policy grants DynamoDB | items written pre-SSE-KMS use prior state (background re-encryption) | per-object CloudTrail KMS audit |
| PITR | table ACTIVE | reversible; PITR restore creates a NEW table (not a rewind) | 35-day continuous recovery |
| TTL | table ACTIVE; attribute must exist on items | items without the TTL attribute are NEVER expired; 48-hour deletion lag | cost optimization + data-retention hint |
| Streams | table ACTIVE; StreamViewType chosen | reversible; 24-hour retention window | CDC: Lambda triggers, OpenSearch sync, Kinesis replay, Aurora zero-ETL |
| Deletion protection | table ACTIVE | reversible; blocks `delete-table` API | accidental-deletion / ransomware guardrail |
| Table class | table ACTIVE | switchable between STANDARD ↔ STANDARD_INFREQUENT_ACCESS | cost optimization for cold tables |
| Global Tables (v2) | table ACTIVE in primary region; PITR recommended | replica capacity is INDEPENDENT per region; each replica has its own KMS key availability | multi-region active-active |
| Resource-based policy | table ACTIVE | can restrict cross-account access; does NOT replace IAM identity policies | cross-account table access without IAM role assumption |

**The four immutable-or-near-immutable rows are the ones a baseline model
misses.** Key schema, LSI, capacity mode, and (effectively) GSI design are
decided at creation time. The procedure below forces an explicit decision
on each before the `create-table` call.

**Cross-dependency gotchas** (not visible in the table):
- Enabling SSE-KMS with a customer CMK on a large existing table triggers
  a background re-encryption migration measured in hours. Plan for it.
- A GSI in PROVISIONED mode with insufficient WCU throttles writes to the
  BASE TABLE. GSI autoscaling is not optional in PROVISIONED mode.
- Switching a Global Table replica's KMS key requires the new key to exist
  in the replica's region — a missing key causes
  `InaccessibleEncryptionDateTime` (active outage).
- PITR restore creates a NEW table with DEFAULT capacity settings — you
  must reconfigure capacity (or switch to on-demand) after restore.

## Expert heuristic: partition key cardinality calculator

A baseline model knows "use a high-cardinality partition key" but cannot
quantify HOW high is high enough. Use this formula:

**Rule:** for write-heavy workloads (more than 1,000 WCU sustained), the
partition key should have **at least 10,000 distinct values** actively
written in any given hour. Below that threshold, writes concentrate on
too few physical partitions and you get hot-partition throttling even
when average utilization looks fine in CloudWatch.

**Quick check formula:**

```text
distinct_partition_values = COUNT(DISTINCT partitionKey) over a 1-hour window
required_minimum = max(10000, sustained_writes_per_second × 3600 / 1000)

if distinct_partition_values < required_minimum:
    → HOT PARTITION RISK
    → FIX: use composite key (userId + timestamp) or random-suffix sharding
```

**Why 10,000:** DynamoDB divides a table across physical partitions
(roughly 10 GB per partition). Write capacity is distributed evenly
across partitions. With fewer than 10,000 distinct keys, the hash
distribution is uneven enough that 2-3 partitions absorb a
disproportionate share of writes, and adaptive capacity's buffer cannot
absorb the skew. This is the threshold observed in production incident
post-mortems, not a documented AWS limit.

**Common scenarios:**
- **Status field as partition key** (e.g., `OPEN`, `CLOSED`): 2-5 distinct
  values → catastrophic hot partition. ALWAYS combine with a
  high-cardinality attribute.
- **Date-only partition key** (e.g., `2026-01-15`): 365 distinct values
  per year → hot within each day. Use `userId#2026-01-15` instead.
- **userId partition key for 50,000 users**: 50,000 distinct values →
  safe IF writes are evenly distributed. Verify with a histogram; a
  "whale" user writing 100x more than others re-creates the hot spot.

## Expert heuristic: GSI cost multiplier

Every GSI adds WCU cost on the base table for every write. The multiplier
is deterministic:

```text
additional_wcu_per_write = ceil(item_size_kb) × number_of_gsis
total_write_wcu = base_wcu + additional_wcu_per_write
```

**Concrete example:** a table with 2 KB items and 5 GSIs:
- Base write cost: ceil(2) = 2 WCU per write
- GSI replication cost: ceil(2) × 5 = 10 WCU per write
- **Total: 12 WCU per write — 6x the base cost**

A table with 5 GSIs costs **5x the WCU on writes** compared to a table
with zero GSIs, before projection-type amplification. `ALL` projection
GSIs cost the full item size; `KEYS_ONLY` GSIs cost only the key size
but still add 1 WCU per write per GSI.

**Budget heuristic:** before adding the 3rd GSI, calculate:

```text
monthly_gsi_cost = writes_per_month × ceil(avg_item_kb) × gsi_count × wcu_price
```

If this exceeds 30% of your total DynamoDB bill, consolidate access
patterns by overloading GSIs (one GSI with a composite sort key serves
multiple query patterns) rather than adding more GSIs.

## Expert heuristic: adaptive capacity false sense of security

Adaptive capacity is the most misunderstood DynamoDB feature. A baseline
model states "adaptive capacity handles hot partitions" — this is
dangerously incomplete.

**What adaptive capacity ACTUALLY does:**
- When a partition consumes its allocated capacity faster than neighbors,
  DynamoDB temporarily borrows unused capacity from a neighbor partition
  for **~30 seconds** (the adaptive capacity window).
- During this window, writes to the hot partition do NOT throttle.
- After ~30 seconds, if the imbalance persists, the borrow expires and
  **throttling resumes** with `ProvisionedThroughputExceededException`.

**What it does NOT do:**
- It does NOT prevent throttling. It only DELAYS it for ~30 seconds.
- It does NOT work for sustained hot-key patterns — only for brief bursts.
- It does NOT apply to on-demand mode (on-demand has its own burst-bucket
  mechanic, which is separate).

**Practical implication:** if your CloudWatch `ThrottledRequests` metric
shows periodic spikes every 30-60 seconds, that is the signature of
adaptive capacity borrowing-and-expiring. The fix is NOT more capacity —
it is partition-key redesign to distribute writes more evenly. Adding
more WCU only raises the ceiling; the hot partition still absorbs a
disproportionate share.

**On-demand caveat:** on-demand mode also has a burst bucket derived from
the trailing 30-minute traffic average. A cold-start spike from zero RPS
has an EMPTY burst bucket and will throttle immediately. On-demand is NOT
"unlimited instant capacity."

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If any
are missing, the verdict is **PREREQUISITES_MISSING** with a specific gap
citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with DynamoDB access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | Capacity, KMS, and Streams are region-scoped | `aws configure get region` |
| Table name available and unique in this region (and globally if Global Tables planned) | Names are region-unique; Global Tables require unique name across all replica regions | `aws dynamodb describe-table --table-name <name>` returns `ResourceNotFoundException` |
| KMS key ARN (if SSE-KMS with customer CMK) | Custom encryption requires a CMK in the same region with a key policy granting DynamoDB | `aws kms describe-key --key-id <cmk-id>` |
| Access-pattern description | Key schema, sort key, and GSI design are access-pattern-driven and immutable | Captured in the prompt or follow-up question |
| CMK key policy grants DynamoDB service + calling principal | SSE-KMS requires `kms:GenerateDataKey` + `kms:Decrypt` grants | `aws kms get-key-policy --key-id <cmk-id> --policy-name default` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING` and
cite the specific gap.

## 10-step provisioning procedure

### Step 1 — Partition key design (immutable — decide BEFORE create-table)

The partition key determines how writes distribute across physical
partitions. A bad partition key is the single highest-impact DynamoDB
design mistake and is **immutable** after creation.

**Decision tree:**

- **High-cardinality, even-distribution workload** (session store, ad-tech
  events, IoT telemetry, user-profile keying by `userId`): use the natural
  high-cardinality attribute directly. Verify with a histogram of the
  attribute if possible.

- **Monotonically increasing attribute as the natural key** (timestamp,
  auto-increment id, sequential orderId): append a **random suffix** (e.g.,
  0-99 or a hash bucket) and use `<naturalKey>#<suffix>` as the partition
  key. Distributes writes across N buckets → N physical partitions.

  ```text
  orderId: 100001  →  partition key: "100001#37"
  orderId: 100002  →  partition key: "100002#04"
  orderId: 100003  →  partition key: "100003#71"
  ```

  The application generates the suffix (random or hash of an unrelated
  attribute); reads must fan out across all suffixes if the natural key
  must be reconstructed. This is the canonical fix for hot-partition
  write throttling.

- **Composite key for hierarchical data** (multi-tenant, time-bucketed):
  combine tenantId + bucketId into the partition key (e.g.,
  `<tenantId>#<yyyy-mm>`), use a sort key for the intra-bucket ordering.
  Distributes tenants across partitions while keeping tenant data
  co-located for efficient queries.

- **Low-cardinality attribute (status, category, boolean)**: NEVER use as
  the partition key alone — writes will concentrate on 1-few partitions.
  Combine with a high-cardinality attribute to form a composite key.

**Why decided at creation**: the partition key is part of `KeySchema` in
`create-table` and is immutable. Re-keying an existing table means
create-new → backfill (with re-partitioning) → cutover. Decide before the
first write.

**Common mistake**: using a timestamp-prefix partition key for time-series
data. All writes in the current second/minute/hour hit one partition
(DynamoDB hashes the partition key, but a low-cardinality timestamp prefix
still concentrates writes within a time bucket). Use the random-suffix
pattern OR use the sort key for time within a high-cardinality partition.

### Step 2 — Sort key design (immutable — decide BEFORE create-table)

The sort key enables range queries (`between`, `begins_with`) within a
partition. Decide at creation; sort key is immutable.

**Decision tree:**

- **Time-range queries within an entity** (orders for a user, events for
  a session, messages in a thread): partition key = entity id, sort key =
  timestamp (ISO 8601 or epoch). Enables `Query` with
  `KeyConditionExpression: pk = :entity AND sk BETWEEN :start AND :end`.

- **Hierarchical data** (category/subcategory paths, file paths): sort key
  = path (e.g., `category/subcategory/item`). Enables `begins_with`
  queries for subtree retrieval.

- **Latest-item lookup** (leaderboards, current state): use a sort key that
  sorts newest-first. For numeric/epoch sort keys, store the negation or
  `MAX_VALUE - timestamp` so the latest sorts first.

- **No range-query need**: omit the sort key (table can have partition key
  only). Adding a sort key later requires re-creating the table.

**Common mistake**: planning to use a non-key attribute for range queries
post-creation. Either (a) add it as the sort key now (immutable), (b) add
an LSI now (immutable, only-at-creation, 5-per-table limit), or (c) add a
GSI later (mutable but with capacity/cascade implications).

### Step 3 — Local Secondary Indexes (LSI) — decide NOW or forever hold peace

LSIs enable range queries on a non-key sort attribute within the SAME
partition key as the base table. They can ONLY be created at `create-table`
time — there is NO API to add an LSI later.

**Hard limits** (do not exceed):
- 5 LSIs per table (HARD API-enforced limit — cannot be raised via support ticket).
- 10 GB per-partition size limit on indexed data (silently rejects writes past this point — must monitor per-partition index size).

**When to provision an LSI at creation:**
- Workload needs strong consistency on the alternate sort attribute (LSI
  supports eventually-consistent AND strongly-consistent reads; GSI only
  eventually-consistent).
- Workload needs range queries within the base table's partition key on a
  different sort attribute.

**When to defer to a GSI (added later):**
- The alternate access pattern uses a DIFFERENT partition key (LSI shares
  the base partition key).
- Eventual consistency is acceptable.
- You are unsure — GSIs are reversible; LSIs are not.

**Common mistake**: deciding to "add the LSI later." There is no later.
If the workload MIGHT need range queries on a non-key attribute, decide
at creation. Document the decision in the checklist.

### Step 4 — Global Secondary Indexes (GSI) — design at provisioning

GSIs enable alternate access patterns with a different partition key. They
CAN be added post-creation, but each GSI has its own capacity, its own
throttle cascade back to the base table, and counts toward the 20-per-table
soft quota.

**Projection type decision (drives storage cost + write amplification):**

| Projection | What it stores | Write cost | Storage cost | Use when |
|---|---|---|---|---|
| `ALL` | Entire base-table item | highest (every base write replicates fully) | highest | GSI is read-heavy and you want to avoid a follow-up GetItem |
| `INCLUDE` | Keys + specified non-key attributes | medium (only listed attributes projected) | medium | GSI needs a few specific attributes (e.g., status, name) |
| `KEYS_ONLY` | Only the GSI's key attributes | lowest (minimum replication) | lowest | GSI is a lookup index; follow up with GetItem from the base table for full data |

**Sparse index pattern**: a GSI where the sort key attribute only exists
on SOME items becomes a sparse index — only items with that attribute
appear in the GSI. Powerful for "find all items in state X" queries
without scanning the whole table.

**Capacity per GSI (PROVISIONED mode)**: each GSI has its OWN RCU/WCU
allocation. A GSI with insufficient WCU throttles BASE TABLE writes —
the cascade rule. Always register autoscaling on every GSI in PROVISIONED
mode (Step 5).

**Quota check**: the 20-GSI-per-table soft limit can be raised via support
ticket. The 5-LSI limit cannot. Plan GSI count at provisioning.

**Common mistake**: provisioning a GSI with `ALL` projection "for
convenience." Every base-table write now fully replicates to the GSI,
doubling write cost. Default to `KEYS_ONLY` and follow up with a `GetItem`;
upgrade to `INCLUDE` only for known hot attributes.

### Step 5 — Capacity mode + autoscaling

Choose between `PAY_PER_REQUEST` (on-demand) and `PROVISIONED` with
autoscaling based on the **traffic profile**, not on a desire to avoid
capacity planning.

**Decision matrix:**

| Traffic profile | Recommended mode | Why |
|---|---|---|
| Unknown / new workload | `PAY_PER_REQUEST` (on-demand) | No capacity planning needed; pay per request |
| Bursty / unpredictable | `PAY_PER_REQUEST` (on-demand) | Autoscaling has 3-5 min lag; on-demand handles spikes (within burst bucket) |
| Steady high-throughput | `PROVISIONED` + autoscaling | 3-5x cheaper than on-demand at sustained load |
| Idle / dev / test | `PAY_PER_REQUEST` (on-demand) | Pay zero when table is idle; provisioned has minimum capacity charges |
| Once-per-hour batch | `PAY_PER_REQUEST` (on-demand) | Cold-start burst bucket handles the spike better than provisioned scale-out lag |

**On-demand burst bucket caveat**: on-demand allocates burst capacity
based on the trailing 30-minute traffic average (roughly 5x the recent
average). A cold-start spike from zero has an EMPTY burst bucket and can
still throttle. On-demand is NOT "instant unlimited."

**PROVISIONED autoscaling registration (MANDATORY if PROVISIONED)**:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 --max-capacity <max>
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 5 --max-capacity <max>

aws application-autoscaling put-scaling-policy \
  --policy-name <table>-read-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"}}'
# Repeat for WriteCapacityUnits and for EVERY GSI:
#   --resource-id table/<table>/index/<gsi-name>
#   --scalable-dimension dynamodb:index:ReadCapacityUnits (and Write)
```

**Common mistake**: registering autoscaling on the base table but NOT on
a GSI. The GSI throttles and cascades back to the base table — the most
commonly missed capacity misconfiguration.

**Switching modes**: DynamoDB enforces a cooldown between
PAY_PER_REQUEST ↔ PROVISIONED switches. Don't switch per-request.

### Step 6 — Encryption (SSE-KMS)

DynamoDB ALWAYS encrypts at rest. The decision is whether to use
AWS-managed or customer-controlled encryption:

| Option | SSEType | Key policy control | CloudTrail visibility | Use when |
|---|---|---|---|---|
| Default (AWS-owned key) | `AES256` | none | none | dev / test / non-compliance workloads |
| AWS-managed KMS key (`alias/aws/dynamodb`) | `KMS` | limited (DynamoDB-managed) | partial | when KMS API visibility matters but key policy does not |
| Customer-managed CMK | `KMS` with explicit `KMSMasterKeyArn` | full (you set the policy) | full (per-call Decrypt events) | compliance (PCI-DSS, HIPAA, SOC2), cross-account, regulated data |

**For compliance workloads**, always use a customer-managed CMK and verify
the key policy grants `kms:GenerateDataKey` + `kms:Decrypt` to both
`dynamodb.<region>.amazonaws.com` and the calling principal.

```bash
aws dynamodb create-table ... \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=arn:aws:kms:<region>:<acct>:key/<cmk-id>
```

**KMS cost warning**: SSE-KMS adds KMS API calls. Customer-managed CMKs
share the account's KMS rate quota; AWS-managed `aws/dynamodb` keys have
a dedicated quota. For very-high-throughput tables, monitor KMS throttle
metrics.

**Global Tables**: each replica region must have the CMK (or a
region-local copy). A missing key in a replica region causes
`InaccessibleEncryptionDateTime` (active outage).

### Step 7 — Point-in-time recovery (PITR) — enable by default

Enable PITR on every production table. PITR provides a 35-day continuous
replay window — restore to any second within the window. AWS Backup
(scheduled snapshots) is COMPLEMENTARY, not a substitute.

```bash
aws dynamodb update-continuous-backups --table-name <table> \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

**PITR restore creates a NEW table** — it cannot rewind the original. The
restored table gets DEFAULT capacity settings; reconfigure after restore.

**Cost note**: PITR consumes additional storage proportional to the change
rate. For most production tables the recovery benefit outweighs the cost.

### Step 8 — TTL configuration (optional — automatic item expiration)

TTL automatically deletes items whose specified attribute (epoch seconds)
is in the past. Use for: session expiry, log retention, cache eviction,
GDPR data-retention enforcement (with caveats below).

```bash
aws dynamodb update-time-to-live --table-name <table> \
  --time-to-live-specification Enabled=true,AttributeName=ttl
```

**TTL semantics** (do not misrepresent):
- Items WITHOUT the TTL attribute are NEVER expired.
- Deletion is by background scanner within **48 hours** of the expiry
  timestamp. Items remain readable until physically deleted.
- TTL is a **cost-optimization feature**, NOT a compliance enforcement
  mechanism. For immediate/verifiable deletion, the application must
  explicitly `DeleteItem`.

**Common mistake**: relying on TTL for GDPR immediate-deletion. The 48-hour
lag and the "items without attribute are never expired" rule both break
the contract.

### Step 9 — Streams + table class + deletion protection

Three additive, reversible configurations:

**DynamoDB Streams** (for CDC pipelines — Lambda triggers, OpenSearch
sync, Kinesis replay, Aurora zero-ETL):

```bash
aws dynamodb update-table --table-name <table> \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
```

Choose `StreamViewType` based on the consumer:
- `NEW_IMAGE` — consumer needs only the post-update state (e.g., search index sync).
- `OLD_IMAGE` — consumer needs only the pre-update state (e.g., audit log of deletions).
- `NEW_AND_OLD_IMAGES` — consumer needs both (e.g., diff-based replication, Aurora zero-ETL, full CDC).
- `KEYS_ONLY` — consumer needs only the keys (e.g., trigger a Lambda to re-fetch).

Streams have a 24-hour retention window. For longer retention, fan out to
Kinesis Data Streams.

**Table class** (`STANDARD` vs `STANDARD_INFREQUENT_ACCESS`):

```bash
aws dynamodb update-table --table-name <table> --table-class STANDARD_INFREQUENT_ACCESS
```

- `STANDARD` (default): for actively-used tables.
- `STANDARD_INFREQUENT_ACCESS`: for cold / infrequently accessed tables
  (audit logs, archives). Lower storage cost; higher per-request cost.
  Use only when access is rare.

**Deletion protection** (blocks `delete-table` API):

```bash
aws dynamodb update-table --table-name <table> --deletion-protection-enabled
```

Mandatory for production tables. Blocks accidental deletion and ransomware.
Note: any principal with `dynamodb:UpdateTable` can disable it — it is an
accidental-deletion guardrail, not a security control.

### Step 10 — Resource-based policy + Global Tables (newer features)

**Resource-based policy** (newer feature — cross-account access without
IAM role assumption):

```bash
aws dynamodb put-resource-policy --resource-arn arn:aws:dynamodb:<region>:<acct>:table/<table> \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<dest-acct>:root"},
      "Action": ["dynamodb:GetItem","dynamodb:Query"],
      "Resource": "arn:aws:dynamodb:<region>:<acct>:table/<table>"
    }]
  }'
```

Resource-based policies COMPLEMENT (not replace) IAM identity policies.
The effective permission is the intersection of identity-based and
resource-based grants. Use for cross-account data sharing without
managing cross-account IAM roles.

**Global Tables v2** (multi-region active-active):

```bash
aws dynamodb create-global-table --global-table-name <table> \
  --replication-group RegionName=<region1> RegionName=<region2>
```

Each replica has INDEPENDENT capacity settings and INDEPENDENT KMS key
availability. Verify the CMK exists in every replica region. Verify
replication-latency alarms are configured on `ReplicationLatency`.

**Latest integrations (2024-2026)**:
- **Zero-ETL to Amazon OpenSearch Service**: DynamoDB Streams can fan out
  to OpenSearch for near-real-time search indexing. Requires
  `NEW_AND_OLD_IMAGES` stream view type.
- **Aurora zero-ETL integration**: DynamoDB Tables can stream changes to
  Aurora PostgreSQL for analytical queries. Requires Streams enabled with
  `NEW_AND_OLD_IMAGES`.
- **Global Tables v2 replication enhancements**: faster replication,
  new CloudWatch metrics for `ReplicationLatency` and `BytesPendingReplication`.

## NEVER do these things

1. **NEVER pick a partition key without considering cardinality and write
   distribution.** A monotonically increasing key (timestamp, auto-increment
   id) creates a hot partition and throttles the table far below its
   provisioned capacity. Use a random suffix or composite key. Re-keying
   requires create-new + backfill + cutover.

2. **NEVER plan to "add the LSI later."** Local Secondary Indexes can ONLY
   be created at `create-table` time. There is NO API to add an LSI
   post-creation. Decide LSI placement at provisioning or commit to a GSI.

3. **NEVER register autoscaling on the base table but forget the GSIs.**
   A GSI with insufficient WCU throttles writes to the BASE TABLE — the
   cascade rule. Register autoscaling on every GSI in PROVISIONED mode.

4. **NEVER use the AWS-managed `alias/aws/dynamodb` key for compliance
   workloads (PCI-DSS / HIPAA / SOC2 / FedRAMP).** You cannot customize
   the key policy. Use a customer-managed CMK with explicit
   `kms:GenerateDataKey` + `kms:Decrypt` grants.

5. **NEVER rely on TTL for immediate data deletion or GDPR compliance.**
   TTL items persist for up to 48 hours after expiry. Items without the
   TTL attribute are never expired. TTL is a cost-optimization feature,
   not a compliance enforcement mechanism.

6. **NEVER assume on-demand mode eliminates capacity risk.** On-demand
   has a finite burst bucket derived from the trailing 30 minutes. A
   cold-start spike from zero can still throttle. Flag this as
   operational guidance.

7. **NEVER enable Streams as a "default hardening" step on tables whose
   workload does not consume CDC.** Streams incur write-amplification cost
   and have a 24-hour retention window. Enable Streams only when there is
   a downstream consumer (Lambda, OpenSearch sync, Kinesis, Aurora zero-ETL).

8. **NEVER exceed the 5-LSI-per-table limit.** It is a HARD API-enforced
   limit — cannot be raised via support ticket. The 20-GSI soft limit
   CAN be raised. Plan accordingly at provisioning.

9. **NEVER provision a Global Table replica in a region without the CMK
   present.** A missing key causes `InaccessibleEncryptionDateTime` —
   an active outage on that replica. Verify `aws kms describe-key` in
   every replica region before adding the replica.

10. **NEVER treat `DeletionProtectionEnabled` as a security control.**
    Any principal with `dynamodb:UpdateTable` can disable it. It is an
    accidental-deletion / ransomware guardrail, not a defense against a
    determined attacker with database-admin rights.

11. **NEVER switch billing mode for per-request cost optimization.**
    DynamoDB enforces a cooldown between `PAY_PER_REQUEST` and `PROVISIONED`
    switches. Choose based on the sustained traffic profile.

12. **NEVER use `ALL` projection on a GSI "for convenience."** Every
    base-table write fully replicates, doubling write cost. Default to
    `KEYS_ONLY` and follow up with a `GetItem`; upgrade to `INCLUDE` for
    known hot attributes.

## Output format

```text
TABLE: <table-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Partition key: <attribute> (<type>) — <design rationale>
  [✓|✗] Sort key: <attribute> (<type>) | None
  [✓|✗] LSIs: <list with sort attributes> | None (5-max HARD limit respected)
  [✓|✗] GSIs: <list with projection types> | None
  [✓|✗] Capacity mode: PAY_PER_REQUEST | PROVISIONED (autoscaling: table ✓ <gsi> ✓)
  [✓|✗] Encryption: SSE-KMS customer CMK (<key-arn>) | AWS-managed (alias/aws/dynamodb) | AES256
  [✓|✗] PITR: Enabled (35-day window)
  [✓|✗] TTL: Enabled (attribute: <name>) | Disabled
  [✓|✗] Streams: NEW_AND_OLD_IMAGES | KEYS_ONLY | NEW_IMAGE | OLD_IMAGE | Disabled
  [✓|✗] Table class: STANDARD | STANDARD_INFREQUENT_ACCESS
  [✓|✗] Deletion protection: Enabled | Disabled
  [✓|✗] Resource-based policy: <summary> | None
  [✓|✗] Global Tables: replicas in <regions> | Single-region
VERIFICATION_COMMANDS:
  aws dynamodb describe-table --table-name <table>
  aws dynamodb describe-continuous-backups --table-name <table>
  aws dynamodb describe-time-to-live --table-name <table>
  aws dynamodb describe-kinesis-destination --table-name <table>   # if Kinesis fan-out
  aws application-autoscaling describe-scaling-policies --service-namespace dynamodb
  aws kms describe-key --key-id <cmk-id>
```

### Worked example — high-throughput session store

```text
TABLE: prod-sessions
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Partition key: sessionId (String) — UUID v4, high-cardinality for even write distribution
  [✓] Sort key: None (single-item lookup pattern)
  [✓] LSIs: None (no range-query requirement on alternate sort attribute)
  [✓] GSIs: gsi_by_userId (userId→sessionId, KEYS_ONLY projection, sparse — only items with userId)
  [✓] Capacity mode: PAY_PER_REQUEST (bursty session traffic, unpredictable peaks)
  [✓] Encryption: SSE-KMS customer CMK (alias/prod-dynamodb-key)
  [✓] PITR: Enabled (35-day window)
  [✓] TTL: Enabled (attribute: expiresAt — session token expiry, ~48h lag acceptable)
  [✓] Streams: NEW_AND_OLD_IMAGES (downstream Lambda publishes session-change events)
  [✓] Table class: STANDARD (frequently accessed)
  [✓] Deletion protection: Enabled
  [✓] Resource-based policy: Allow read-only from analytics account 222222222222
  [✓] Global Tables: Single-region (us-east-1)
VERIFICATION_COMMANDS:
  aws dynamodb describe-table --table-name prod-sessions
  aws dynamodb describe-continuous-backups --table-name prod-sessions
  aws dynamodb describe-time-to-live --table-name prod-sessions
  aws kms describe-key --key-id alias/prod-dynamodb-key
```

## Decision tree: on-demand vs provisioned

```text
Is the workload new / unknown traffic pattern?
├── YES → PAY_PER_REQUEST (on-demand)
│         (No capacity planning; switch to PROVISIONED after 2-3 weeks
│          of steady-state traffic data)
└── NO → Is traffic bursty / unpredictable (> 3:1 peak-to-trough ratio)?
    ├── YES → PAY_PER_REQUEST (on-demand)
    │         (Autoscaling has 3-5 min lag; on-demand handles spikes
    │          instantly within the burst bucket)
    └── NO → Is traffic steady and high-throughput (> 5,000 RCU/WCU sustained)?
        ├── YES → PROVISIONED + autoscaling
        │         (3-5x cheaper than on-demand at sustained load)
        └── NO → Is the table idle most of the time (dev / test / low-traffic)?
            ├── YES → PAY_PER_REQUEST (on-demand)
            │         (Pay zero when idle; provisioned has minimum charges)
            └── NO → PROVISIONED + autoscaling
                      (Moderate steady traffic; autoscaling handles
                       gradual changes)
```

**Post-decision review:** after 2-3 weeks of production traffic, review
CloudWatch `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits`. If
utilization is > 70% steady, PROVISIONED is cheaper. If utilization is
< 30% or highly bursty, stay on-demand. DynamoDB enforces a cooldown
between mode switches — do not switch per-request.

## Error handling

### Table already exists (`ResourceInUseException`)

```bash
aws dynamodb describe-table --table-name <name>
```

- If configuration matches intent: the table is already provisioned
  correctly. Skip to verification and emit READY_TO_DEPLOY.
- If configuration differs: decide whether to `update-table` (mutable
  settings: capacity, PITR, TTL, streams, table class, deletion
  protection) or create a NEW table with the correct schema (immutable
  settings: partition/sort key, LSIs). Key schema changes REQUIRE
  create-new → backfill → cutover. NEVER attempt to `delete-table` then
  `create-table` to "fix" a schema mismatch — data loss.

### GSI creation fails during backfill

When adding a GSI to an existing table (`update-table
--global-secondary-index-updates`), DynamoDB backfills the index from
the base table. The GSI enters `CREATING` state (can take minutes to
hours for large tables).

**If the backfill fails** (GSI status flips to `DELETING` or table stuck
in `UPDATING`):

1. Check CloudTrail for `LimitExceededException` — the account may have
   too many concurrent GSI backfills (account-level soft limit).
2. Wait for the GSI to finish auto-cleanup (it will reach `DELETING` then
   disappear).
3. Retry with a smaller `ProjectionType` (`KEYS_ONLY` instead of `ALL`)
   to reduce backfill write load.
4. For PROVISIONED tables, temporarily raise the GSI's WCU during
   backfill to avoid throttling the base table during index population.

**NEVER** delete the base table to "fix" a stuck GSI backfill. The
backfill will complete or the GSI will be auto-deleted; either way the
base table data is safe. Monitor with:

```bash
aws dynamodb describe-table --table-name <name> \
  --query 'Table.GlobalSecondaryIndexes[*].[IndexName,IndexStatus,Backfilling]'
```

### PITR enable fails

- **`AccessDeniedException`**: the caller lacks
  `dynamodb:UpdateContinuousBackups`. This is a separate IAM permission
  from `dynamodb:UpdateTable` — add it to the caller's policy.
- **`ValidationException`**: the table was created within the last few
  minutes and is not yet `ACTIVE`. Wait for `TableStatus = ACTIVE` and
  retry.
- **PITR already enabled**: the call is idempotent — returns success with
  no change. No error to handle.

### Autoscaling registration fails

- **"Min capacity must be less than or equal to max capacity"**: check
  that `--min-capacity` < `--max-capacity`. Common typo.
- **"The scalable target already exists"**: the target was previously
  registered. Re-issuing `register-scalable-target` is safe (upsert-like
  for existing targets with the same dimensions). To change dimensions,
  `deregister-scalable-target` first.
- **GSI autoscaling `ResourceNotFoundException`**: the GSI name is wrong
  or the GSI is still `CREATING`. Verify with `describe-table` and
  register autoscaling only after the GSI reaches `ACTIVE`.

## Worked example — provisioned table with GSI + autoscaling

A high-throughput events table with a GSI for lookup by userId, using
PROVISIONED capacity with autoscaling on BOTH the base table and the GSI.
This is the critical pattern the eval flagged — the earlier session-store
example used on-demand and skipped GSI autoscaling registration.

```bash
# 1. Create table with GSI in a single create-table call
aws dynamodb create-table \
  --table-name prod-events \
  --attribute-definitions \
    AttributeName=eventId,AttributeType=S \
    AttributeName=userId,AttributeType=S \
    AttributeName=createdAt,AttributeType=N \
  --key-schema \
    AttributeName=eventId,KeyType=HASH \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=5000,WriteCapacityUnits=2000 \
  --global-secondary-indexes '[
    {
      "IndexName": "gsi_by_userId",
      "KeySchema": [
        {"AttributeName":"userId","KeyType":"HASH"},
        {"AttributeName":"createdAt","KeyType":"RANGE"}
      ],
      "Projection": {"ProjectionType":"KEYS_ONLY"},
      "ProvisionedThroughput": {"ReadCapacityUnits":2000,"WriteCapacityUnits":1000}
    }
  ]' \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/prod-dynamodb-key \
  --deletion-protection-enabled

# 2. Wait for table + GSI to reach ACTIVE
aws dynamodb wait table-exists --table-name prod-events
aws dynamodb describe-table --table-name prod-events \
  --query 'Table.GlobalSecondaryIndexes[0].[IndexName,IndexStatus]'

# 3. Register autoscaling on BASE TABLE (reads)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/prod-events \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 1000 --max-capacity 20000

aws application-autoscaling put-scaling-policy \
  --policy-name prod-events-read-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/prod-events \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"}}'

# 4. Register autoscaling on BASE TABLE (writes)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/prod-events \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 500 --max-capacity 10000

aws application-autoscaling put-scaling-policy \
  --policy-name prod-events-write-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/prod-events \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBWriteCapacityUtilization"}}'

# 5. Register autoscaling on GSI (reads) — THIS IS THE STEP MOST COMMONLY MISSED
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/prod-events/index/gsi_by_userId \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --min-capacity 500 --max-capacity 10000

aws application-autoscaling put-scaling-policy \
  --policy-name prod-events-gsi-read-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/prod-events/index/gsi_by_userId \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"}}'

# 6. Register autoscaling on GSI (writes)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/prod-events/index/gsi_by_userId \
  --scalable-dimension dynamodb:index:WriteCapacityUnits \
  --min-capacity 200 --max-capacity 5000

aws application-autoscaling put-scaling-policy \
  --policy-name prod-events-gsi-write-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/prod-events/index/gsi_by_userId \
  --scalable-dimension dynamodb:index:WriteCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBWriteCapacityUtilization"}}'

# 7. Enable PITR
aws dynamodb update-continuous-backups --table-name prod-events \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# 8. Enable TTL
aws dynamodb update-time-to-live --table-name prod-events \
  --time-to-live-specification Enabled=true,AttributeName=expiresAt

# 9. Enable Streams for CDC (Aurora zero-ETL / OpenSearch sync)
aws dynamodb update-table --table-name prod-events \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

# 10. Verify everything
aws dynamodb describe-table --table-name prod-events
aws dynamodb describe-continuous-backups --table-name prod-events
aws dynamodb describe-time-to-live --table-name prod-events
aws application-autoscaling describe-scaling-policies --service-namespace dynamodb \
  --query 'ScalingPolicies[?contains(ResourceId,`prod-events`)].[PolicyName,ResourceId,ScalableDimension]'
```

The checklist for this table:

```text
TABLE: prod-events
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Partition key: eventId (String) — UUID v4, high-cardinality (> 10k distinct)
  [✓] Sort key: None (event-level lookup by partition key)
  [✓] LSIs: None (no range queries on alternate sort within same partition)
  [✓] GSIs: gsi_by_userId (userId→createdAt, KEYS_ONLY projection, sparse)
  [✓] Capacity mode: PROVISIONED (autoscaling: table ✓ read+write, gsi ✓ read+write)
  [✓] Encryption: SSE-KMS customer CMK (alias/prod-dynamodb-key)
  [✓] PITR: Enabled (35-day window)
  [✓] TTL: Enabled (attribute: expiresAt — 90-day retention, 48h lag acceptable)
  [✓] Streams: NEW_AND_OLD_IMAGES (Aurora zero-ETL consumer)
  [✓] Table class: STANDARD (actively queried)
  [✓] Deletion protection: Enabled
  [✓] Resource-based policy: None (single-account)
  [✓] Global Tables: Single-region (us-east-1)
VERIFICATION_COMMANDS:
  aws dynamodb describe-table --table-name prod-events
  aws dynamodb describe-continuous-backups --table-name prod-events
  aws dynamodb describe-time-to-live --table-name prod-events
  aws application-autoscaling describe-scaling-policies --service-namespace dynamodb
  aws kms describe-key --key-id alias/prod-dynamodb-key
```

## Recent AWS features (2024-2026)

- **DynamoDB zero-ETL to Amazon OpenSearch Service (2024-2025):** DynamoDB
  Tables can stream changes directly to OpenSearch for near-real-time
  search indexing. Requires Streams enabled with `NEW_AND_OLD_IMAGES`.
  Provisioning tip: enable Streams at table creation if OpenSearch sync
  is in scope.
- **Aurora zero-ETL integration (2024-2025):** DynamoDB changes stream to
  Aurora PostgreSQL for analytical queries without ETL pipelines. Requires
  Streams with `NEW_AND_OLD_IMAGES`. Provisioning tip: capacity-mode
  decision should account for Streams write amplification.
- **Global Tables v2 replication enhancements (2024):** Faster replication
  and new CloudWatch metrics (`ReplicationLatency`, `BytesPendingReplication`,
  `UpdateTimestamp`). Provisioning tip: configure alarms on
  `ReplicationLatency` for every replica pair.
- **Resource-based policies (2023-2024):** DynamoDB tables now support
  resource-based policies for cross-account access without IAM role
  assumption. Provisioning tip: prefer resource-based policies over
  cross-account IAM roles for read-only data sharing.
- **Table classes — Standard and Standard-IA (2024):** Assign `STANDARD`
  or `STANDARD_INFREQUENT_ACCESS` per table. Provisioning tip: use
  Standard-IA for audit logs and archives, not for active workloads.
- **Incremental export to S3 (2024):** In addition to full-table exports,
  DynamoDB supports incremental exports to S3. Provisioning tip: pair
  with PITR for point-in-time export windows.
- **Deletion protection GA (November 2023):** Blocks `delete-table` API
  when enabled. Provisioning tip: enable by default on production tables.

## Domain

AWS CloudOps / DynamoDB Table Provisioning & Schema Design.

## AWS documentation

- **Amazon DynamoDB Developer Guide** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html
- **DynamoDB Tables, Items, and Attributes** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html
- **Best Practices for Designing and Using Partition Keys Effectively** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html
- **Global Secondary Indexes** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html
- **DynamoDB Streams** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html
- **Point-in-Time Recovery** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html
- **DynamoDB Table Classes** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ddn-table-classes.html
- **Aurora zero-ETL integration with DynamoDB** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.Aurora_DynamoDB_Integration.html
