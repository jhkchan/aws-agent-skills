# Advanced Patterns — Redshift Query Troubleshooter

Philosophy behaviours, Step 0 non-obvious behaviours, distribution/sort pattern tables, WLM queue types, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Philosophy — four senior-engineer behaviours

Four behaviours separate a senior Redshift engineer from a generalist:

- **The EXPLAIN output's scan type tells you the problem.** A `Seq
  Scan` means a full table scan -- no sort key elimination. A
  `DS_DIST_NONE` means the join is co-located -- no network
  redistribution. A `DS_DIST_ALL_INNER` means the inner table is
  broadcast to all nodes -- a costly operation on large tables. An
  `XN Nested Loop` means a Cartesian product -- almost always a
  missing join condition. These three signals eliminate 80% of
  performance diagnosis.

- **Distribution style (KEY vs ALL vs EVEN) is a join-time decision.**
  `DISTSTYLE KEY` on the join column co-locates matching rows on the
  same slice, enabling `DS_DIST_NONE` joins. `DISTSTYLE ALL`
  replicates the full table to every node (good for small dimension
  tables, bad for large fact tables). `DISTSTYLE EVEN` distributes
  randomly -- joins always require redistribution. Choosing the wrong
  distribution style for the workload's dominant join pattern is the
  #1 cause of slow queries.

- **Sort keys are for range elimination, not just ordering.** A sort
  key on `sale_date` enables Redshift's zone maps to skip 1 MB blocks
  that fall outside the query's date range. Without a sort key on the
  filter column, every query scans the entire table. The sort key
  should match the column most frequently used in range predicates
  (WHERE, BETWEEN, >=).

- **WLM queue hopping can hide queue timeout root causes.** With WLM
  Query Queue Hopping, a query that times out in one queue is
  automatically moved to the next queue. The query eventually succeeds
  (or times out in the last queue), but the operator sees a long total
  wait time. The root cause is the first queue being overloaded, not
  the query being slow.


## Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior Redshift engineer knows
from incident experience:

- **DISTSTYLE KEY requires the join column to be the dist key on BOTH
  tables.** A fact table distributed on `customer_id` joined to a
  dimension table distributed on `store_id` forces a network
  redistribution (DS_DIST_ALL_INNER or DS_DIST_OUTER). The fix is
  either making both tables KEY-distributed on the join column, or
  making the smaller table DISTSTYLE ALL.

- **DISTSTYLE ALL is not free.** An ALL-distributed table is fully
  replicated on every node. For a small dimension table (under ~2-5
  million rows), this is efficient -- joins are always local
  (DS_DIST_NONE). For a large table, ALL wastes storage and slows
  writes. Never use ALL on a fact table.

- **Compound sort keys are ordered.** A compound sort key on
  `(sale_date, store_id)` is only effective for queries that filter on
  `sale_date` or `sale_date AND store_id`. A query filtering on
  `store_id` alone gets NO sort key benefit because `store_id` is the
  second column. The first column of a compound sort key is always the
  most selective filter.

- **Interleaved sort keys are not magic.** An interleaved sort key on
  `(sale_date, store_id)` gives equal weight to both columns, enabling
  zone map elimination for queries filtering on either column alone.
  But interleaved sorts are expensive to maintain (VACUUM takes
  longer), and performance degrades with more than 3-4 interleaved
  columns.

- **WLM queue timeout counts queue wait, not execution time.** A
  query that spends 4 minutes waiting in the queue and 10 seconds
  executing is cancelled at the 4-minute mark if the WLM timeout is
  4 minutes. The fix is to reduce queue contention (add slots, tune
  queue assignment), not to optimize the query.

- **COPY requires the IAM role to have S3 read access.** The cluster's
  IAM role must have `s3:GetObject` on the bucket and path. A COPY
  that fails with "S3ServiceException: Access Denied" is always an
  IAM role issue, not a COPY syntax issue.

- **COPY from S3 manifest mismatch is subtle.** If the manifest file
  lists files that don't exist, or the manifest URL prefix is wrong,
  COPY fails with a load error that looks like a format error. Always
  verify the manifest contents separately.

- **STL_LOAD_ERRORS has one row per error, not per failed COPY.** A
  single COPY of a large file with multiple bad rows generates many
  STL_LOAD_ERRORS entries. Focus on the first error (lowest starttime)
  -- it usually identifies the root cause (wrong delimiter, wrong
  encoding, missing column).

- **Vacuum requires exclusive access to the table for the sort phase.**
  A VACUUM sorts the table to reclaim space and re-sort unsorted
  regions. If concurrent writes are occurring, the VACUUM may stall
  waiting for write locks. In busy clusters, schedule VACUUM during
  low-write windows.

- **Nested loop joins are almost always bugs.** A nested loop join
  (DS_DIST_NONE with no hash join) means Redshift could not find a
  join condition it could hash on. This usually means a missing join
  condition, a data type mismatch on the join column, or a join on a
  UDF output. The query plan shows `XN Nested Loop DS_DIST_NONE`.

- **Connection limits are cluster-level, not user-level.** The total
  number of connections is capped by the cluster's node count and
  type. Each connection consumes server-side resources. Connection
  pooling (via pgbouncer or a connection pooler) is essential for
  high-concurrency workloads.

- **Encoding conversion errors come from the client, not the data.** A
  "character with byte sequence ... has no equivalent in encoding"
  error means the client's encoding (e.g., UTF-8) cannot represent a
  character in the data's encoding (e.g., Latin-1). The fix is to set
  the client encoding to match the data, or to clean the data.


## Step 5 — key distribution patterns

Key distribution patterns:

| Scenario | EXPLAIN shows | Root cause |
|---|---|---|
| Both tables KEY on join column | `DS_DIST_NONE` | Optimal -- no redistribution. |
| One table EVEN, other KEY | `DS_DIST_ALL_INNER` | EVEN table must be redistributed. Change to KEY on join column. |
| Both tables EVEN | `DS_DIST_ALL_INNER` | Both redistributed. Choose a dist key for both. |
| Small dimension table is KEY (not ALL) | `DS_DIST_ALL_INNER` | Change small table to DISTSTYLE ALL for DS_DIST_NONE. |
| Large fact table DISTSTYLE ALL | N/A (wastes storage) | Never use ALL on large tables. |

## Step 6 — sort key issue effects

If `sortkey1` is empty or does not match the query's filter column:

| Sort key issue | Effect |
|---|---|
| No sort key | Every query is a full `Seq Scan`. Zone maps cannot eliminate blocks. |
| Sort key on wrong column | Zone maps exist but are useless for the query's actual filter. |
| Compound sort key, query filters on 2nd column | No zone map benefit; the first column of a compound key dominates. |
| `unsorted` is high (> 20%) | The table has many unsorted rows. Run VACUUM SORT to re-sort. |

## Step 7 — nested loop join meaning

A nested loop join means Redshift performs a Cartesian product --
every row in one table is matched against every row in another. This
is almost always a bug.

## Step 8 — connection limit model

The connection limit depends on the cluster's node count and type.
Each node supports a fixed number of connections (typically 500 per
node for most types, shared across all databases).

## WLM queue types

### WLM queue types

| Queue (service_class) | Default purpose | Typical config |
|---|---|---|
| Queue 1-5 | System / maintenance | Managed by Redshift |
| Queue 6+ | User-defined | Configurable via WLM |
| Superuser queue | DBA operations | Accessed via `SET query_group TO 'superuser'` |

With Automatic WLM (default on newer clusters), Redshift dynamically
manages memory and concurrency. Manual WLM queues are defined in the
parameter group via `wlm_json_configuration`.

## Recent AWS features (2024-2026)

- **Automatic WLM (2024-2025):** Redshift dynamically manages query
  queue memory and concurrency. Manual WLM queue tuning is less
  critical on clusters with Auto WLM enabled, but queue timeout
  configuration still matters.
- **Redshift Serverless (2024-2025):** Workgroup-based, no cluster
  management. WLM concepts change to RPU (Redshift Processing Unit)
  scaling. Connection limits scale with base RPU capacity.
- **Late materialization for sort keys (2024):** Redshift defers
  fetching column data until after zone map filtering, improving scan
  performance on wide tables with selective sort keys.
- **AUTO DISTSTYLE and AUTO SORTKEY (2024-2025):** Redshift can
  automatically select distribution style and sort keys based on
  query patterns. Use `ALTER TABLE ... ALTER DISTSTYLE AUTO` to
  enable.
- **Data API enhancements (2024-2025):** The Redshift Data API now
  supports longer-running queries and better error messages, making
  it viable for programmatic diagnosis without a persistent JDBC
  connection.
- **Concurrency scaling (2024-2025):** Redshift automatically adds
  transient clusters to handle burst query workloads. WLM queue
  contention may be mitigated by concurrency scaling, but the root
  cause of queue saturation should still be addressed.
