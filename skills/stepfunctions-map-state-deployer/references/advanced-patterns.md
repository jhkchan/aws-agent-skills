# Step Functions Map State Deployer - advanced patterns (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Mindset - three dominant Map-state misconceptions

Three misconceptions dominate Map state misdesign at provisioning time:

- **"Inline Map and Distributed Map are interchangeable."** They are
  NOT. Inline Map runs within the parent execution context — it shares
  the parent's execution history, has a hard 5000-item limit, and adds
  NO extra cost. Distributed Map spawns child executions — each batch is
  a separate execution with its own history, has a 10000-item limit, and
  incurs per-child-execution cost. Choosing Inline for a 7000-item array
  FAILS at runtime. Choosing Distributed for a 50-item array wastes
  money on unnecessary child executions.

- **"Iterator and ItemProcessor are the same thing."** They are related
  but NOT interchangeable. `Iterator` is the legacy field name (pre-2022)
  that defines the sub-workflow to run for each item. `ItemProcessor` is
  the current field that replaces `Iterator` and adds
  `ProcessorConfig` (which controls Inline vs Distributed mode). A
  state machine using `Iterator` cannot use Distributed Map — only
  `ItemProcessor` with `Mode: DISTRIBUTED` enables it. Mixing
  `Iterator` with Distributed configuration is a silent failure.

- **"Distributed Map just runs faster."** It runs differently. Each
  batch in Distributed Map is a SEPARATE child execution, meaning: (1)
  each batch has its own execution ARN and history, (2) the parent
  execution's history does NOT grow with item count, (3) the
  ToleratedFailureCount/Percentage settings control how many batches can
  fail before the Map state fails, and (4) each child execution counts
  against your account's concurrent execution quota. The speedup is
  from parallelism (MaxConcurrency), not from a fundamentally different
  processing model within a single execution.

## Expert heuristic: ItemProcessor vs Iterator

The `Iterator` field was the original way to define the sub-workflow for
a Map state. In 2022, AWS introduced `ItemProcessor` as a replacement,
adding `ProcessorConfig` to control Inline vs Distributed mode.

```text
Legacy (pre-2022) — Inline only:
  "Map": {
    "Type": "Map",
    "Iterator": {
      "StartAt": "ProcessItem",
      "States": { ... }
    },
    "ItemsPath": "$.items"
  }

Current (2022+) — supports Inline AND Distributed:
  "Map": {
    "Type": "Map",
    "ItemProcessor": {
      "ProcessorConfig": {
        "Mode": "INLINE"  // or "DISTRIBUTED"
      },
      "StartAt": "ProcessItem",
      "States": { ... }
    },
    "ItemsPath": "$.items"
  }
```

**Key implication:** if you see `Iterator` in a state machine, it is
implicitly Inline. You CANNOT use Distributed Map with `Iterator` —
switch to `ItemProcessor` with `ProcessorConfig.Mode: DISTRIBUTED`. Do
NOT mix both fields; validation will fail.

## Expert heuristic: batch processing with ItemBatchSize

ItemBatchSize groups multiple items into a single batch, reducing the
number of child executions in Distributed Map. This is critical for
throughput and cost efficiency.

```text
Without ItemBatchSize (1 item per child execution):
  10000 items → 10000 child executions
  Each child processes 1 item
  High overhead, high cost, high concurrency pressure

With ItemBatchSize: 100 (100 items per child execution):
  10000 items → 100 child executions
  Each child processes 100 items (received as an array)
  Lower overhead, lower cost, lower concurrency pressure
```

**Critical:** the ItemProcessor sub-workflow receives a BATCH (array of
items), not a single item. The sub-workflow must iterate within the
batch using `States.Intrinsic` functions or a nested Map state. For
single-item processing, keep ItemBatchSize at 1 (default).

**Key implication:** ItemBatchSize is a throughput and cost lever, not a
functional one. It does not change WHAT is processed — it changes HOW
MANY items each child execution handles.

## Step 10 - cost model deep dive

**Inline Map cost:** ZERO additional cost beyond the parent execution.
The Map iterations run within the parent execution context. The parent
execution's state transition count includes all iterations.

**Distributed Map cost:** each child execution is a SEPARATE billable
execution. For 1000 items with `ItemBatchSize: 1`, that is 1000 child
executions. With `ItemBatchSize: 100`, it is 10 child executions — a
100x cost reduction.

```text
Cost example — 10000 items, Standard workflow:
  Inline Map: 0 child executions → $0 extra
    (but may exceed 5000-item limit)

  Distributed Map, ItemBatchSize=1:
    10000 child executions
    Each child: ~15 state transitions × $0.025/1000 = $0.000375
    Total: 10000 × $0.000375 = $3.75

  Distributed Map, ItemBatchSize=100:
    100 child executions
    Each child: ~15 state transitions × $0.025/1000 = $0.000375
    Total: 100 × $0.000375 = $0.0375 (100x cheaper)
```

## Step 11 - Recent features

**Recent AWS features (2023-2026):**

- **ItemBatcher (2023):** Replaced ItemBatchSize with a richer
  configuration object supporting MaxItemsPerBatch,
  MaxInputBytesPerBatch, and BatchInput. ItemBatchSize remains supported
  as a simpler alternative.

- **Timestream as Distributed Map input (2024-2025):** Distributed Map
  can now use Amazon Timestream query results as an input source, in
  addition to S3. This enables time-series data processing workflows
  without pre-materializing data into S3.

- **Firehose as Distributed Map input (2024-2025):** Amazon Kinesis
  Data Firehose delivery streams can serve as input sources for
  Distributed Map, enabling near-real-time batch processing of streaming
  data.

- **ToleratedFailureCount (2023-2024):** Added as a complement to
  ToleratedFailurePercentage for fine-grained partial failure control.
  Both can be set simultaneously; the Map fails if EITHER threshold is
  exceeded.

- **Express Workflow Distributed Map (2023-2024):** Distributed Map now
  supports Express Workflows (previously Standard only). Child
  executions of Express type are billed at Express pricing (per-invocation
  + per-execution-duration).

- **Child execution Label (2023-2024):** The `Label` field on
  Distributed Map allows custom naming of child executions, making it
  easier to identify which parent execution spawned which children.

