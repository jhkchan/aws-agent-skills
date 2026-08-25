# Advanced Patterns (load on demand) — DynamoDB Table Deployer

Mindset, reasoning framework, dependency graph, expert heuristics, Step 10 newer features, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Mindset (moved from SKILL.md)

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

---

## Reasoning framework (why provisioning order matters) (moved from SKILL.md)

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

---

## DynamoDB configuration dependency graph (novel heuristic) (moved from SKILL.md)

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

---

## Expert heuristic: partition key cardinality calculator (moved from SKILL.md)

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

---

## Expert heuristic: GSI cost multiplier (moved from SKILL.md)

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

---

## Expert heuristic: adaptive capacity false sense of security (moved from SKILL.md)

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

---

## Step 5 on-demand burst bucket caveat (moved from SKILL.md)

**On-demand burst bucket caveat**: on-demand allocates burst capacity
based on the trailing 30-minute traffic average (roughly 5x the recent
average). A cold-start spike from zero has an EMPTY burst bucket and can
still throttle. On-demand is NOT "instant unlimited."

---

## Step 6 KMS cost warning and Global Tables CMK requirement (moved from SKILL.md)

**KMS cost warning**: SSE-KMS adds KMS API calls. Customer-managed CMKs
share the account's KMS rate quota; AWS-managed `aws/dynamodb` keys have
a dedicated quota. For very-high-throughput tables, monitor KMS throttle
metrics.

**Global Tables**: each replica region must have the CMK (or a
region-local copy). A missing key in a replica region causes
`InaccessibleEncryptionDateTime` (active outage).

---

## Step 10 — Resource-based policy + Global Tables (newer features) (moved from SKILL.md)

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

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

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
