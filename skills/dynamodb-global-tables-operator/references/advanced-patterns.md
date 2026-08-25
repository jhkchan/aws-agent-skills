# Advanced Patterns (load on demand) — DynamoDB Global Tables Operator

Expert heuristics, Step 0 expert-knowledge behaviors, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Expert heuristic — non-obvious global table behaviours (moved from SKILL.md)

- **Adding a replica copies data from an existing replica, not from
  the "primary."** The new replica's data is bootstrapped from a
  snapshot of the closest existing replica. During the CREATING phase,
  the new replica is not writable. Monitor `ReplicaStatus` transitioning
  to `ACTIVE`.

- **Removing a replica is irreversible.** Once `update-global-table`
  removes a replica, the data in that region is deleted. There is no
  "pause replication" — the table in the removed region is permanently
  deleted. Always verify the region is no longer needed before removal.

- **Schema changes propagate but are not instantaneous.** A GSI added
  to the primary region must be explicitly created on each replica.
  DynamoDB does not auto-propagate GSI changes across replicas. Use
  `update-table` in each region for GSI additions.

- **Billing mode changes must be applied to all replicas.** Switching
  from PROVISIONED to PAY_PER_REQUEST on one replica does not switch
  the others. Apply billing mode changes region by region.

- **`describe-global-table` returns the global table view; `describe-table`
  returns the regional view.** Operators must check both. A replica may
  be `ACTIVE` in the global table view but `UPDATING` in the regional
  `describe-table` output (e.g., during GSI rebuild).

- **ReplicationLatency is measured per region pair, not per item.**
  CloudWatch `ReplicationLatency` shows the average time for a write
  to replicate from one region to another. High latency does not mean
  data is lost — it means the replication pipeline is slow. Data will
  eventually arrive unless the replica is deleted.

- **Concurrent writes from multiple regions with the same partition
  key can cause thrashing under LWW.** If two regions continuously
  update the same item, the LWW resolution flips the value back and
  forth. This is not a conflict — it is the expected behavior. Design
  the access pattern to avoid concurrent cross-region writes to the
  same key.

- **PITR restore on a global table replica creates a NEW single-region
  table.** The restored table is NOT a global table — it does not
  replicate to other regions. To restore a global table, restore in
  one region, then recreate the global table from the restored table.

- **Autoscaling policies must be registered per replica region.**
  Global table replication does not copy autoscaling policies. Each
  replica needs its own `register-scalable-target` and
  `put-scaling-policy` calls.

- **Global Tables write cost scales linearly with replica count.** A
  write to a 3-replica global table consumes 3x the WCU of a
  single-region write. The replicated write cost is the single-region
  WCU × (number of replicas). Budget accordingly.

---

## Step 0: Expert knowledge — non-obvious Global Tables behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational experience.
Each changes a plan if ignored:

- **`create-global-table` requires identical empty tables in all target
  regions first.** For a new global table, create the table in each
  region with the same key schema and billing mode, THEN call
  `create-global-table`. The tables must be EMPTY (no items). DynamoDB
  then links them into a global table.

- **Adding a replica to an existing global table does NOT require a
  pre-created table.** `update-global-table --replica-updates
  '[{Create:{RegionName:<region>}}]'` creates the new replica table
  automatically in the target region. Data is copied from an existing
  replica.

- **The global table name must match the regional table name.** If the
  table is called `orders-prod` in `us-east-1`, it must be
  `orders-prod` in every replica region. The global table name is also
  `orders-prod`. This is not configurable.

- **Conflict resolution is `LAST_WRITER_WINS` with no alternative.**
  Global Tables v2 does not support custom conflict resolution. The
  application must be designed for LWW semantics. For counters or
  append-heavy workloads, use DynamoDB Streams to merge, not direct
  cross-region writes.

- **Replication is asynchronous.** A write to region A replicates to
  region B within typically < 1 second, but there is no synchronous
  guarantee. An application reading from region B immediately after
  writing to region A may see stale data. Use read-after-write
  consistency within a single region only.

- **Per-region PITR is independent.** Enabling PITR on the primary
  does NOT enable it on replicas. For DR, enable PITR on EVERY replica
  region. The cost is per-region per-GB.

- **Removing the last replica is equivalent to deleting the global
  table.** If you remove all replicas except one, the global table
  becomes a single-region table. The replication metadata is removed.
  Re-adding replicas later requires going through the full add-replica
  process.

- **`describe-global-table-settings` shows per-region autoscaling and
  replica-specific configuration.** This is separate from
  `describe-global-table` which shows only replication group membership.
  Always check both before operations.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Global Tables v2 is the only supported version (2024+).** The
  original Global Tables (v1) is deprecated. All new global tables
  must use the v2 API (`create-global-table`, `update-global-table`).
  Existing v1 tables should be migrated to v2.

- **Per-region PITR independence confirmed (2024-2025).** PITR can be
  enabled/disabled independently on each replica region. This is the
  recommended DR posture: enable PITR on every replica so each region
  has its own 35-day recovery window.

- **Improved ReplicationLatency metrics (2024):** CloudWatch now
  provides per-region-pair ReplicationLatency with finer granularity.
  Use `ReceivingRegion` dimension to track latency for each replica
  independently.

- **Global Tables cost optimization (2025):** the replicated write
  cost is now transparently reported in Cost Explorer per replica
  region. Use the `DB_INSTANCE_IDENTIFIER` dimension (or Cost Tags)
  to attribute cost per region.

- **Multi-region strong consistency preview (2025-2026):** AWS has
  previewed an optional strong-consistency mode for Global Tables that
  uses a quorum-based protocol instead of LWW. This is not yet GA —
  most workloads still use LWW. Check the latest documentation before
  assuming strong consistency is available.

- **Global Tables with DeleteProtectionEnabled (2024):** per-region
  deletion protection prevents accidental table deletion in any
  replica region. Enable this on all production global table replicas.
