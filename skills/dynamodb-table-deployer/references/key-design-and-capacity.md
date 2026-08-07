# Key Design and Capacity Guide — DynamoDB Table Deployer

Deep reference on partition-key shaping, sort-key patterns, GSI projection
tradeoffs, LSI vs GSI selection, on-demand burst behavior, and provisioned
autoscaling timing. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Partition key shaping patterns

The partition key determines how writes distribute across physical
partitions. DynamoDB hashes the partition key to pick a physical partition;
items with the same partition key live on the same physical partition and
are served by a fixed amount of throughput. A "hot partition" is one that
receives disproportionate traffic — it throttles even when the rest of the
table has spare capacity.

### Pattern 1 — Natural high-cardinality key (no shaping)

Use when the natural attribute has high cardinality AND even write
distribution. Examples: UUID v4 session IDs, hashed userIds where the
population writes evenly.

**Verify before commit**: histogram the attribute. If the top 1% of keys
receive >5% of writes, the distribution is uneven — apply shaping.

### Pattern 2 — Random suffix (write-heavy monotonic key)

Use when the natural key is monotonically increasing (timestamp, sequential
orderId, auto-increment id). Append a random suffix:

```text
partitionKey = f"{naturalKey}#{random_int(0, N-1)}"
# Example: N=100 buckets
"100001#37", "100002#04", "100003#71"
```

**Tradeoff**: a read by the natural key must fan out to all N buckets and
merge (parallel `Query` calls). Pick N large enough to distribute writes
(N >= peak_write_rate / per_partition_capacity) but small enough that fan-out
reads stay cheap.

**Variant — hash-bucketed suffix** (deterministic reads): use
`hash(naturalKey) % N` instead of random. Reads by the natural key hit ONE
bucket; reads still distribute across buckets across keys. Loses the
"spread a single hot key across buckets" property.

### Pattern 3 — Composite key for hierarchical / multi-tenant data

Combine two concerns into the partition key, use the sort key for ordering:

```text
partitionKey = f"{tenantId}#{yyyy-mm}"    # tenant + month bucket
sortKey      = orderId                    # intra-bucket ordering
```

**Why**: keeps a tenant's monthly data co-located on a small number of
partitions (efficient tenant queries) while distributing across tenants and
months. The bucketing dimension (month) prevents any single partition from
growing unbounded.

### Pattern 4 — Sharded hot key (extreme write concentration)

For a SINGLE logical entity that receives extreme write volume (e.g., a
global counter, a popular item's comments), pre-shard the entity:

```text
partitionKey = f"{entityId}#shard-{random_int(0, N-1)}"
# Writes: pick a random shard per write
# Reads: query all N shards in parallel and aggregate
```

The application layer aggregates reads. Use only when a single logical
entity is the bottleneck — adds read complexity.

### Anti-patterns

- **Timestamp prefix as partition key** (e.g., `2024-08-07#sessionId`):
  all writes within the same day land on one partition. Use the timestamp
  as the SORT KEY with a high-cardinality partition key instead.
- **Status / category as partition key** (e.g., `status=ACTIVE`): all
  active items on one partition. Use a GSI with the status as the GSI
  partition key and the item's unique id as the sort key — and even then,
  watch for skew.
- **Sequential userId lexicographic ordering**: if userIds are issued
  sequentially, the newest users cluster on adjacent partitions — write
  skew toward "newest users" creates hot spots. Use a hash of the userId
  instead.

## Sort key patterns

The sort key enables range queries (`BETWEEN`, `begins_with`) WITHIN a
partition. Sort key choice is immutable after `create-table`.

### Time-range queries

```text
partitionKey = userId
sortKey      = 2024-08-07T14:30:00Z   (ISO 8601)
# Query: userId = :u AND sortKey BETWEEN :start AND :end
```

For epoch numeric sort keys: store `MAX_LONG - timestamp` if the workload
mostly reads the newest items (sorts descending in original time → ascending
in stored form).

### Hierarchical / prefix queries

```text
partitionKey = forumId
sortKey      = "category/subcategory/postId"
# Query: forumId = :f AND begins_with(sortKey, "category/subcategory/")
```

This retrieves a whole subtree in one query.

### Versioned / immutable records

```text
partitionKey = documentId
sortKey      = version         (integer or timestamp)
# Query: top 1 sortKey desc → latest version
```

### Reverse lookup via GSI

If the access pattern is "given attribute X, find the item," and X is not
the partition key, use a GSI with X as the GSI partition key. The sort key
on the GSI can be a different attribute.

## GSI projection type — cost and consistency

| Projection | Stored in GSI | Write amplification | Storage | Read pattern |
|---|---|---|---|---|
| `ALL` | entire base item | every base write fully replicates | highest | GSI returns full item — no follow-up |
| `INCLUDE` | keys + listed non-key attributes | only listed attributes project | medium | GSI returns listed attributes; follow-up GetItem for others |
| `KEYS_ONLY` | only GSI partition + sort key | minimum replication | lowest | GSI returns keys; follow-up GetItem for full item |

**Rule of thumb**: default to `KEYS_ONLY`. Upgrade to `INCLUDE` for known
hot attributes (avoids the follow-up GetItem round trip). Reserve `ALL` for
read-heavy GSIs where the follow-up cost is unacceptable.

### Sparse index pattern

A GSI becomes sparse when its sort key attribute exists only on SOME items.
Only items with that attribute appear in the GSI — a powerful pattern for
"find all items in state X" without scanning.

```text
# Base table
partitionKey = orderId, attributes: status, total, ...
# GSI
partitionKey = status, sortKey = orderId
# Only items with a non-null status appear in the GSI.
# Query gsi where status = "PENDING" returns only pending orders.
```

## LSI vs GSI — selection matrix

| Property | LSI | GSI |
|---|---|---|
| Created at table creation only | YES (HARD constraint) | No (can add later) |
| Per-table quota | 5 (HARD limit, cannot raise) | 20 (soft, can raise) |
| Partition key | SAME as base table | DIFFERENT from base table |
| Consistency | strong OR eventual | eventual only |
| Per-partition size limit | 10 GB (silently rejects past this) | none analogous |
| When to use | range queries on alternate sort attribute, same partition | alternate access pattern, different partition key |
| When NOT to use | if you might exceed 10 GB per partition; if workload needs eventual consistency only | if workload needs strong consistency on the alternate key |

**Decision rule**: if the alternate access pattern uses the SAME partition
key as the base table AND needs strong consistency OR you are sure the
10 GB per-partition limit will not bite, use LSI. Otherwise use GSI.

## On-demand burst capacity internals

On-demand mode maintains a burst capacity bucket. Approximate sizing:
**trailing 30-minute traffic average × 5**.

| Trailing 30-min average | Burst bucket (approx) |
|---|---|
| 1,000 RCU/s sustained | ~5,000 RCU/sec burst for short spikes |
| 0 (cold start) | empty — first spike throttles |
| 10,000 RCU/s sustained | ~50,000 RCU/sec burst |

**Implication**: on-demand is NOT "instant unlimited." A workload with
prolonged zero-then-spike cycles (e.g., once-per-hour batch) may throttle
on every spike. For such patterns, provisioned with autoscaling (warmer
baseline) or pre-warming the table with steady low traffic may work better.

## Provisioned autoscaling timing internals

Target-tracking autoscaling evaluates a CloudWatch alarm every 1 minute
with a 2-minute evaluation period. The pipeline:

1. CloudWatch metric `DynamoDBReadCapacityUtilization` (table or index).
2. Alarm fires when utilization > target (default 70%) for 2 consecutive
   minutes.
3. Application Auto Scaling issues `UpdateTable` to modify provisioned
   throughput.
4. New capacity takes effect within seconds of the API call.

End-to-end lag: **3-5 minutes** from spike onset to capacity landing. For
sub-minute traffic spikes, provisioned + autoscaling WILL throttle before
scaling completes — on-demand is the correct choice for unpredictable
bursts.

### Autoscaling target value

- **Target 70%**: balanced — leaves 30% headroom for in-flight scale-out.
- **Target 50%**: conservative — more headroom, higher steady-state cost.
- **Target 90%**: cost-aggressive — minimal headroom, throttle risk on
  fast spikes.

Default recommendation: **70%**.

### GSI autoscaling (MANDATORY in PROVISIONED mode)

A GSI in PROVISIONED mode has its OWN RCU/WCU allocation. Insufficient GSI
capacity throttles BASE TABLE writes (cascade rule). Register autoscaling
on EVERY GSI in PROVISIONED mode — base-table autoscaling does NOT cover
GSIs.

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/<table>/index/<gsi-name> \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --min-capacity 5 --max-capacity <max>
# Repeat for WriteCapacityUnits
```

## Switching capacity modes

DynamoDB enforces a cooldown between `PAY_PER_REQUEST` ↔ `PROVISIONED`
switches (on the order of minutes). Frequent switching for per-request
cost optimization does not work — DynamoDB prevents capacity-gaming.

**Choose once based on traffic profile**:
- Unknown / bursty / unpredictable → `PAY_PER_REQUEST`
- Steady high-throughput → `PROVISIONED` + autoscaling
- Idle / dev / test → `PAY_PER_REQUEST` (pay zero when idle)

## PITR restore mechanics

`RestoreTableToPointInTime` creates a NEW table — it cannot overwrite the
source. Key constraints:

- Restored table name must be unique (cannot overwrite source).
- Restored table gets DEFAULT capacity settings (NOT source's settings) —
  reconfigure after restore.
- Restore is asynchronous — large tables take minutes to hours.
- Indexes (GSI/LSI) from source are recreated on the restored table.
- The restore does NOT include Streams configuration or CloudWatch alarms
  — reconfigure separately.

## Global Tables v2 — per-replica independence

Each Global Tables replica has INDEPENDENT:
- Capacity settings (RCU/WCU or on-demand) — set per-replica.
- PITR configuration — enable per-replica.
- KMS key availability — the CMK must exist in EACH replica region.
- Table class — can differ per-replica (rare).

**Common Global Tables mistakes at provisioning**:
- Forgetting to provision the CMK in a replica region →
  `InaccessibleEncryptionDateTime` → active outage.
- Assuming the primary's autoscaling covers replicas — it does not.
- Assuming replicas inherit PITR — they do not.
- Failing to alarm on `ReplicationLatency` for any replica pair.

## AWS documentation references

- Best Practices for Designing and Using Partition Keys Effectively —
  https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html
- Global Secondary Index Design Patterns —
  https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-indexes.html
- DynamoDB Capacity Modes —
  https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html
- DynamoDB Auto Scaling —
  https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.html
