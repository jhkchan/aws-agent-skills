---
name: stepfunctions-map-state-deployer
description: 'Deploys AWS Step Functions Map state configurations with production defaults: Inline Map (synchronous, max 5000 items, shares parent execution context), Distributed Map (async, max 10000 items via child executions), Map state configuration (ItemsPath, MaxConcurrencyPath, MaxItemsPath, ItemBatchSize, ItemBatcher), ItemProcessor vs Iterator (ItemProcessor is current), batch processing with ItemBatchSize/ItemBatcher for throughput, Distributed Map with S3 input (CSV/JSON/JSONL from S3 via ReaderConfig), child execution quota, ResultSelector/ResultPath, error handling (Retry/Catch per iteration), Parallel state vs Map state (fan-out vs iteration), cost model (Inline = no extra cost, Distributed = child execution cost), and Timestream/Firehose as input source. Emits a READY_TO_DEPLOY checklist with. Triggers: step functions map state, inline map, distributed map, itemprocessor, itembatchsize, maxconcurrency, step functions batch processing, distributed map s3, step functions fan-out, map state error handling.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with stepfunctions access. Works with Terraform aws_sfn_state_machine resources and CloudFormation AWS::StepFunctions::StateMachine templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, step-functions, map-state, distributed-map, cloudops, deploy, app-integration, batch-processing, s3-input, itemprocessor
  dependencies: aws-orchestrator
  keywords: aws, step functions, map state, inline map, distributed map, itemprocessor, itembatchsize, maxconcurrency, cloudops, deploy, batch processing, s3 input, fan-out, child execution
  when_to_use: Invoke when the user wants to configure a Step Functions Map state for array iteration (Inline or Distributed), process items in batches, scale beyond 5000 items with Distributed Map, read large datasets from S3 (CSV/JSON/JSONL), configure MaxConcurrency or ItemBatchSize, set up per-iteration error handling (Retry/Catch), or choose between Inline Map, Distributed Map, and Parallel state. Do NOT invoke for Step Functions Express Workflow cost analysis (use stepfunctions-express- deployer), general state machine creation (use stepfunctions- statemachine-deployer), or execution troubleshooting (use stepfunctions-execution-troubleshooter).
---

# Step Functions Map State Deployer

An AWS CloudOps agent skill that deploys Step Functions Map state
configurations with correct defaults. The skill walks the Inline vs
Distributed Map decision, ItemsPath/MaxConcurrency/ItemBatchSize
configuration, ItemProcessor vs Iterator semantics, Distributed Map with
S3 input, batch processing with ItemBatcher, child execution quota,
ResultSelector/ResultPath, per-iteration error handling, Parallel state
vs Map state, and the cost model, captures the processing topology,
explains why each default matters, and emits a READY_TO_DEPLOY checklist
with copy-pasteable verification commands.

## Activation keywords

Step Functions Map state, Inline Map, Distributed Map, ItemProcessor,
ItemBatchSize, MaxConcurrency, Step Functions batch processing,
Distributed Map S3 input, Map state error handling, Parallel state vs
Map state, ItemBatcher, child execution quota.

## STRICT output contract

When this skill is invoked with a Map-state-provisioning request
(configure a Map state, process arrays in Step Functions, batch
processing items, scale beyond 5000 items, read large datasets from S3,
or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `MAP_STATE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Inline Map vs Distributed Map | Core Map type decision |
| Step 2 — Map state configuration fields | ItemsPath, MaxConcurrency, etc. |
| Step 3 — ItemProcessor vs Iterator | Processor definition |
| Step 4 — Batch processing (ItemBatchSize/ItemBatcher) | Throughput optimization |
| Step 5 — Distributed Map with S3 input | Large dataset ingestion |
| Step 6 — Child execution quota | Distributed Map limits |
| Step 7 — ResultSelector/ResultPath | Result shaping |
| Step 8 — Error handling (Retry/Catch) | Per-iteration resilience |
| Step 9 — Parallel state vs Map state | Fan-out vs iteration |
| Step 10 — Cost model | Inline free vs Distributed child cost |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/map-configuration-and-batching.md | Config + batching detail |
| references/distributed-map-and-s3.md | Distributed Map + S3 detail |

## Mindset

**One-line takeaway:** A Map state iterates over an array of items,
running the same sub-workflow for each item (or batch). Inline Map runs
synchronously within the parent execution (max 5000 items, no extra
cost). Distributed Map runs each batch as a separate child execution
(max 10000 items, incurs child execution cost). Choose Inline for small
arrays; Distributed for large arrays or S3-sourced datasets.

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

## Configuration dependency graph (novel heuristic)

Map state configurations are NOT independent. The Map type (Inline vs
Distributed) determines the item limit, cost model, and whether child
executions are spawned. ItemBatchSize only applies to Distributed Map.
MaxConcurrency controls parallelism in both types but has different
ceiling values. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Map type (Inline/Distributed) | `ItemProcessor.ProcessorConfig.Mode` set correctly | `Iterator` field silently forces Inline mode even if `Mode: DISTRIBUTED` is specified | the processing model |
| ItemsPath | Input must contain a JSON array at the specified path | If ItemsPath is null, the entire input is treated as the array | array iteration |
| MaxConcurrency | Map state defined; value 0 means unlimited | Inline max: 40; Distributed max: 1000 — exceeding silently caps | parallelism control |
| MaxItems / MaxItemsPath | Only supported on Distributed Map | Setting MaxItems on Inline Map is ignored (no error) | item count cap |
| ItemBatchSize | Only supported on Distributed Map; ItemProcessor defined | Setting ItemBatchSize on Inline Map is ignored; range 1-10000 | batch grouping |
| ItemBatcher | Distributed Map; defines batch size, MaxItemsPerBatch, MaxInputBytesPerBatch | Cannot be combined with ItemBatchSize — use ONE not both | advanced batch control |
| ToleratedFailureCount/Percentage | Distributed Map only; error handling | Without this, a single batch failure fails the ENTIRE Map state | partial failure tolerance |
| S3 input (ReaderConfig) | Distributed Map only; S3 bucket/object exists | CSV with > 10K rows requires Distributed Map; Inline cannot read from S3 directly | large dataset ingestion |
| ResultSelector | Map state defined; must produce valid JSON | Applied BEFORE ResultPath; shapes raw result before merging | result shaping |
| ResultPath | Map state defined; must not conflict with input | If null, original input is replaced entirely | result placement |
| Retry/Catch | Defined within ItemProcessor sub-workflow | Per-iteration Retry/Catch is independent across items/batches | per-iteration resilience |

**The ItemBatchSize-on-Inline row is the one a baseline model misses.**
Setting ItemBatchSize on an Inline Map is silently ignored — no error,
no batching. The operator believes batches are being grouped, but each
item runs individually. Only Distributed Map supports ItemBatchSize and
ItemBatcher.

**Cross-dependency gotchas:**
- `Iterator` (legacy) and `ItemProcessor` (current) are mutually
  exclusive. A state machine with BOTH fields will fail validation.
- `ItemBatchSize` and `ItemBatcher` are mutually exclusive. Use
  `ItemBatchSize` for simple fixed-size batches; use `ItemBatcher` for
  advanced control (MaxItemsPerBatch, MaxInputBytesPerBatch).
- `MaxConcurrency: 0` means UNLIMITED, not "no concurrency." This is a
  dangerous default if you expect sequential processing.
- Distributed Map child executions count against the account's
  concurrent execution quota (default 100000). Large batches with high
  MaxConcurrency can exhaust this quota.

## Expert heuristic: Inline vs Distributed decision tree

A baseline model says "use Distributed for large datasets." The correct
heuristic recognizes that the decision depends on item count, input
source, execution history size, cost sensitivity, and partial failure
tolerance.

```text
Map state type decision:
  ├── Item count ≤ 5000 AND input is a JSON array in the state?
  │     → Inline Map (no extra cost, shares parent context)
  ├── Item count > 5000 (up to 10000)?
  │     → Distributed Map (child executions required)
  ├── Input source is S3 (CSV/JSON/JSONL file)?
  │     → Distributed Map (Inline cannot read from S3)
  ├── Input source is Timestream or Firehose?
  │     → Distributed Map (requires child executions for external source)
  ├── Need partial failure tolerance (some batches can fail)?
  │     → Distributed Map (ToleratedFailureCount/Percentage)
  ├── Execution history growing too large (> 25000 entries)?
  │     → Distributed Map (child executions keep parent history small)
  ├── Need batch processing (group items)?
  │     → Distributed Map (ItemBatchSize/ItemBatcher)
  └── Cost-sensitive, small array?
        → Inline Map (free, no child execution charges)
```

**Key implication:** the #1 mistake is choosing Inline Map for a use
case that exceeds its limits (> 5000 items, S3 input, or batch
grouping). The runtime error or silent failure is costly to debug.

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

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| State machine exists or is being created | Map state is part of a state machine | Confirm state machine ARN or ASL definition |
| Input contains a JSON array (for Inline) | Inline Map requires a JSON array in the input | Inspect the input payload or ItemsPath |
| S3 bucket/object exists (for Distributed Map with S3) | Distributed Map reads from S3 at runtime | `aws s3 ls s3://<bucket>/<key>` |
| IAM role has S3 read access (for S3 input) | Distributed Map needs `s3:GetObject` permission | Check IAM policy on the state machine role |
| Item count within limits | Inline: max 5000; Distributed: max 10000 | Verify input array length or S3 row count |
| ItemProcessor defined (not Iterator) | Distributed Map requires ItemProcessor with ProcessorConfig | Inspect ASL definition |
| ToleratedFailureCount/Percentage set (for Distributed) | Without this, one batch failure fails the entire Map | Check Map state configuration |
| MaxConcurrency within range | Inline: max 40; Distributed: max 1000 | Verify MaxConcurrency value |
| Child execution quota sufficient (for Distributed) | Default 100000 concurrent executions per account | Check account quota |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Inline Map vs Distributed Map

The first decision is Inline Map vs Distributed Map. This determines
item limits, cost model, and capabilities.

| Feature | Inline Map | Distributed Map |
|---|---|---|
| Max items | 5000 | 10000 |
| Execution model | Shares parent execution context | Each batch is a separate child execution |
| Cost | No extra cost (included in parent execution) | Per-child-execition cost |
| S3 input | NOT supported | Supported (CSV, JSON, JSONL) |
| Batch processing (ItemBatchSize) | NOT supported | Supported (1-10000 items per batch) |
| MaxConcurrency max | 40 | 1000 |
| Partial failure tolerance | NOT supported | ToleratedFailureCount/Percentage |
| Execution history | Grows with item count (parent history) | Child executions keep parent history small |
| Input payload size | Subject to 256KB execution input limit | Up to 300MB from S3 |
| Mode field | `ProcessorConfig.Mode: INLINE` | `ProcessorConfig.Mode: DISTRIBUTED` |

**Inline Map is the default.** If `ProcessorConfig` is omitted or
`Mode` is not specified, the Map state runs as Inline.

## Step 2 — Map state configuration fields

| Field | Applies to | Description | Default |
|---|---|---|---|
| `ItemsPath` | Both | JSONPath to the array in the input | `$` (entire input) |
| `MaxConcurrencyPath` | Both | JSONPath to a MaxConcurrency value in the input | None (uses MaxConcurrency) |
| `MaxConcurrency` | Both | Max parallel iterations (0 = unlimited) | 0 (unlimited) |
| `MaxItemsPath` | Distributed only | JSONPath to a max items value | None |
| `MaxItems` | Distributed only | Hard cap on number of items processed | None |
| `ItemBatchSize` | Distributed only | Items per child execution batch | 1 |
| `ItemBatcher` | Distributed only | Advanced batch config (MaxItemsPerBatch, MaxInputBytesPerBatch) | None |
| `ItemSelector` | Both | Transforms input before passing to each iteration | None |
| `ToleratedFailureCount` | Distributed only | Number of batch failures tolerated | 0 |
| `ToleratedFailurePercentage` | Distributed only | Percentage of batch failures tolerated | 0 |
| `Label` | Distributed only | Label for child executions (for identification) | None |

**Common mistake:** setting `MaxConcurrency: 0` expecting sequential
processing. Zero means UNLIMITED. For sequential, use
`MaxConcurrency: 1`.

## Step 3 — ItemProcessor vs Iterator

As of 2022, `ItemProcessor` replaces `Iterator`. Key differences:

| Feature | `Iterator` (legacy) | `ItemProcessor` (current) |
|---|---|---|
| Inline Map | Supported | Supported (`Mode: INLINE`) |
| Distributed Map | NOT supported | Supported (`Mode: DISTRIBUTED`) |
| ProcessorConfig | Not available | Available |
| Validation with Mode field | N/A | Required |

**Always use `ItemProcessor`** for new state machines. Only use
`Iterator` when maintaining legacy definitions that cannot be migrated.

```json
{
  "ProcessItems": {
    "Type": "Map",
    "ItemProcessor": {
      "ProcessorConfig": {
        "Mode": "DISTRIBUTED",
        "ExecutionType": "STANDARD"
      },
      "StartAt": "HandleItem",
      "States": {
        "HandleItem": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-item",
          "End": true
        }
      }
    },
    "ItemsPath": "$.items",
    "MaxConcurrency": 10,
    "ItemBatchSize": 50,
    "ToleratedFailurePercentage": 5
  }
}
```

## Step 4 — Batch processing (ItemBatchSize/ItemBatcher)

Batch processing groups multiple items into a single child execution,
reducing overhead and cost in Distributed Map.

**ItemBatchSize (simple):**

```json
{
  "Type": "Map",
  "ItemProcessor": {
    "ProcessorConfig": { "Mode": "DISTRIBUTED" },
    "StartAt": "ProcessBatch",
    "States": {
      "ProcessBatch": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-batch",
        "End": true
      }
    }
  },
  "ItemBatchSize": 100
}
```

**ItemBatcher (advanced):**

```json
{
  "Type": "Map",
  "ItemProcessor": {
    "ProcessorConfig": { "Mode": "DISTRIBUTED" },
    "StartAt": "ProcessBatch",
    "States": { ... }
  },
  "ItemBatcher": {
    "MaxItemsPerBatch": 100,
    "MaxInputBytesPerBatch": 1048576,
    "BatchInput": {
      "timestamp": "2026-08-11T00:00:00Z"
    }
  }
}
```

**ItemBatchSize vs ItemBatcher:**

| Feature | ItemBatchSize | ItemBatcher |
|---|---|---|
| Simplicity | Single integer | Object with multiple fields |
| MaxInputBytesPerBatch | Not configurable | Configurable (default 64KB) |
| BatchInput (extra context per batch) | Not available | Available |
| Mutually exclusive | Yes — use ONE | Yes — use ONE |

**Critical:** the sub-workflow receives a JSON array of items (the
batch), not a single item. The Lambda or sub-workflow must handle an
array input, not a single object.

## Step 5 — Distributed Map with S3 input

Distributed Map can read large datasets directly from S3 (CSV, JSON, or
JSONL files) using `ReaderConfig`.

```json
{
  "ProcessCSV": {
    "Type": "Map",
    "ItemProcessor": {
      "ProcessorConfig": { "Mode": "DISTRIBUTED" },
      "StartAt": "ProcessRow",
      "States": {
        "ProcessRow": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-row",
          "End": true
        }
      }
    },
    "ItemReader": {
      "Resource": "arn:aws:states:::s3:getObject",
      "ReaderConfig": {
        "InputType": "CSV",
        "CSVHeaderLocation": "FIRST_ROW"
      },
      "Parameters": {
        "Bucket": "my-data-bucket",
        "Key": "datasets/records.csv"
      }
    },
    "ItemBatchSize": 100,
    "MaxConcurrency": 50
  }
}
```

**Supported S3 input formats:**

| Format | InputType | Notes |
|---|---|---|
| CSV | `CSV` | First row can be headers (CSVHeaderLocation: FIRST_ROW) |
| JSON (array) | `JSON` | S3 object must contain a JSON array |
| JSONL (JSON Lines) | `JSONL` | One JSON object per line |

**S3 input size limits:**

| Limit | Value |
|---|---|
| Max S3 object size (CSV) | 30 GB |
| Max S3 object size (JSON) | 30 GB |
| Max S3 object size (JSONL) | 30 GB |
| Max items extracted | 10000 |
| Max payload per batch | 64 KB (configurable via MaxInputBytesPerBatch) |

**IAM requirement:** the state machine role needs `s3:GetObject` on the
target bucket/key.

## Step 6 — Child execution quota

Distributed Map spawns child executions. Each child execution counts
against the account's concurrent execution quota.

| Quota | Default | Adjustable |
|---|---|---|
| Concurrent executions per account | 100000 | Yes (Service Quotas) |
| Open child executions per Map state | 10000 | No |
| Items per Map state run | 10000 | No |
| Batches per Map state run | 10000 | No |

**Key implication:** with `MaxConcurrency: 1000` and `ItemBatchSize: 1`,
a 10000-item Distributed Map spawns 10000 child executions. With
`ItemBatchSize: 100`, it spawns 100 child executions. Batch processing
reduces concurrency pressure dramatically.

## Step 7 — ResultSelector/ResultPath

`ResultSelector` and `ResultPath` shape where and how Map state results
are placed in the overall state output.

| Field | Purpose | Placement |
|---|---|---|
| `ResultSelector` | Transforms the raw result BEFORE merging (applied first) | Shapes data |
| `ResultPath` | Where the result goes in the state output | Controls placement |
| `ResultPath: null` | Discards the result (original input passes through) | Drop result |
| `ResultPath: "$.result"` | Places result at `$.result` | Merge with input |

```json
{
  "ProcessItems": {
    "Type": "Map",
    "ItemsPath": "$.items",
    "ItemProcessor": { ... },
    "ResultSelector": {
      "processed_count.$": "$.length(@)",
      "items.$": "$"
    },
    "ResultPath": "$.processing_result",
    "Next": "NotifyComplete"
  }
}
```

**Common mistake:** using `ResultPath: null` when you need the results
for downstream states. This silently discards all iteration outputs.

## Step 8 — Error handling (Retry/Catch per iteration)

Retry and Catch are defined INSIDE the ItemProcessor sub-workflow, not
on the Map state itself. Each iteration (or batch) handles errors
independently.

```json
{
  "ProcessItems": {
    "Type": "Map",
    "ItemProcessor": {
      "StartAt": "CallAPI",
      "States": {
        "CallAPI": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:api-call",
          "Retry": [
            {
              "ErrorEquals": ["States.TaskFailed"],
              "IntervalSeconds": 2,
              "MaxAttempts": 3,
              "BackoffRate": 2.0
            }
          ],
          "Catch": [
            {
              "ErrorEquals": ["States.ALL"],
              "Next": "HandleError",
              "ResultPath": "$.error"
            }
          ],
          "Next": "ProcessResult"
        },
        "ProcessResult": { "Type": "Succeed" },
        "HandleError": { "Type": "Fail" }
      }
    },
    "ToleratedFailurePercentage": 5
  }
}
```

**Distributed Map partial failure:**

- `ToleratedFailureCount`: absolute number of batches that can fail
- `ToleratedFailurePercentage`: percentage of batches that can fail
- If failures exceed the threshold, the Map state fails
- If failures are within tolerance, the Map state succeeds but includes
  failed items in the output

**Key implication:** without `ToleratedFailureCount`/`Percentage` (both
default to 0), a SINGLE batch failure fails the ENTIRE Map state. For
fault-tolerant processing, set one of these.

## Step 9 — Parallel state vs Map state

Both Parallel and Map states fan out work, but they serve different
purposes.

| Feature | Parallel State | Map State |
|---|---|---|
| Purpose | Run DIFFERENT branches concurrently | Run the SAME branch over an array |
| Branches | Each branch is a distinct sub-workflow | Single sub-workflow, repeated per item |
| Input | Same input to all branches | Each item from the array |
| Output | Array of branch results | Array of iteration results |
| Use case | Fan-out of heterogeneous tasks | Iterate over homogeneous items |
| Dynamic items | NOT supported (branches are static) | Supported (array-driven) |
| Distributed mode | NOT supported | Supported (Distributed Map) |

**Decision rule:** use Parallel when branches do DIFFERENT things. Use
Map when the same thing is done for EACH item in an array.

## Step 10 — Cost model

| Component | Inline Map | Distributed Map |
|---|---|---|
| Per-transition cost | Included in parent execution | Included in parent execution |
| Child execution cost | N/A (no child executions) | Each batch = one child execution (billed separately) |
| State transition cost | Billed within parent | Child execution state transitions billed separately |
| S3 GET (for S3 input) | N/A | Standard S3 pricing |

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

**Key implication:** batch processing (ItemBatchSize) is the single most
impactful cost optimization for Distributed Map. Always batch when
possible.

## Step 11 — Recent features

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

## NEVER do these things

1. **NEVER use Inline Map for more than 5000 items.** Inline Map has a
   hard 5000-item limit. It will FAIL at runtime. Use Distributed Map
   for arrays exceeding 5000 items.

2. **NEVER set MaxConcurrency: 0 expecting sequential processing.** Zero
   means UNLIMITED concurrency. For sequential processing, use
   `MaxConcurrency: 1`.

3. **NEVER mix Iterator and ItemProcessor.** They are mutually
   exclusive. A state machine with BOTH fields will fail validation.
   Use ItemProcessor for all new state machines.

4. **NEVER set ItemBatchSize on an Inline Map.** ItemBatchSize is only
   supported on Distributed Map. On Inline Map, it is silently ignored
   — no error, but no batching occurs.

5. **NEVER use Distributed Map without ToleratedFailureCount or
   ToleratedFailurePercentage for fault-tolerant workloads.** Both
   default to 0, meaning a SINGLE batch failure fails the ENTIRE Map
   state. Set at least one tolerance threshold.

6. **NEVER assume the ItemProcessor receives a single item when
   ItemBatchSize > 1.** The sub-workflow receives a BATCH (array of
   items). The Lambda or Task must handle an array input, not a single
   object.

7. **NEVER mix ItemBatchSize and ItemBatcher.** They are mutually
   exclusive. Use ItemBatchSize for simple fixed-size batches; use
   ItemBatcher for advanced control.

8. **NEVER forget the S3 IAM permission for Distributed Map with S3
   input.** The state machine role needs `s3:GetObject` on the target
   bucket/key. Without it, the Map state fails at runtime.

9. **NEVER use Parallel state for array iteration.** Parallel state
   runs DIFFERENT branches concurrently; it does NOT iterate over an
   array. Use Map state for iteration.

10. **NEVER ignore child execution quota.** Each Distributed Map child
    execution counts against the account's concurrent execution quota
    (default 100000). Large batches with high MaxConcurrency can exhaust
    this quota and cause throttling.

## Output format

```text
MAP_STATE: <state-name> (<map-type: INLINE|DISTRIBUTED>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Map type: Inline | Distributed
  [✓|✗] ItemProcessor: defined (Mode: <INLINE|DISTRIBUTED>)
  [✓|✗] ItemsPath: <jsonpath> (input array)
  [✓|✗] MaxConcurrency: <value> (0 = unlimited, Inline max 40, Distributed max 1000)
  [✓|✗] MaxItems: <value|N/A> (Distributed only)
  [✓|✗] ItemBatchSize / ItemBatcher: <value|N/A> (Distributed only)
  [✓|✗] ToleratedFailureCount/Percentage: <value> (Distributed only)
  [✓|✗] S3 input: <bucket/key|N/A> (Distributed only, format <CSV|JSON|JSONL>)
  [✓|✗] ResultSelector: <defined|none>
  [✓|✗] ResultPath: <jsonpath|null|none>
  [✓|✗] Error handling: Retry/Catch per iteration (<defined>)
  [✓|✗] IAM role: <has-s3-access|standard>
  [✓|✗] Item count: <count> (within <Inline 5000 | Distributed 10000> limit)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws stepfunctions describe-state-machine --state-machine-arn <arn>
  aws stepfunctions describe-execution --execution-arn <execution-arn>
```

### Worked example — Distributed Map with S3 CSV input

```text
MAP_STATE: ProcessRecords (DISTRIBUTED)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Map type: Distributed
  [✓] ItemProcessor: defined (Mode: DISTRIBUTED, ExecutionType: STANDARD)
  [✓] ItemsPath: N/A (S3 input via ItemReader)
  [✓] MaxConcurrency: 50
  [✓] MaxItems: 10000
  [✓] ItemBatchSize: 100 (100 items per child execution → 100 child executions max)
  [✓] ToleratedFailurePercentage: 5 (allows up to 5% batch failures)
  [✓] S3 input: s3://my-data-bucket/datasets/records.csv (CSV, FIRST_ROW headers)
  [✓] ResultSelector: { "processed.$": "$" }
  [✓] ResultPath: $.processing_result
  [✓] Error handling: Retry (3 attempts, exponential backoff) + Catch → HandleError
  [✓] IAM role: has s3:GetObject on my-data-bucket
  [✓] Item count: 8500 rows (within Distributed 10000 limit)
  [✓] Tags: Environment=production, Workflow=data-pipeline
VERIFICATION_COMMANDS:
  aws stepfunctions describe-state-machine --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:DataPipeline
  aws stepfunctions describe-execution --execution-arn <execution-arn>
```

## Error handling

### Map state fails with "Items exceed maximum allowed"
- For Inline Map: the input array exceeds 5000 items. Switch to
  Distributed Map.
- For Distributed Map: the input exceeds 10000 items. Reduce the input
  size or split the workflow into multiple runs.

### Distributed Map child execution throttling
- The account's concurrent execution quota is exhausted. Reduce
  MaxConcurrency or increase ItemBatchSize to reduce the number of
  child executions. Request a quota increase via Service Quotas.

### S3 input fails with "Access Denied"
- The state machine IAM role lacks `s3:GetObject` on the target bucket.
  Add the S3 read permission to the role's policy.

### ItemBatchSize silently ignored
- The Map type is Inline, not Distributed. ItemBatchSize only works on
  Distributed Map. Switch to Distributed Map or remove ItemBatchSize.

### Single batch failure fails entire Map state
- ToleratedFailureCount and ToleratedFailurePercentage are both at
  their default (0). Set at least one to allow partial failures.

### Iterator field conflicts with Distributed configuration
- The state machine uses the legacy `Iterator` field, which only
  supports Inline Map. Switch to `ItemProcessor` with
  `ProcessorConfig.Mode: DISTRIBUTED`.

## Domain

AWS CloudOps / AWS Step Functions Map State Configuration & Array
Iteration Processing.

## AWS documentation

- **Map State** — https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-map-state.html
- **Distributed Map state** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-asl-use-map-state-distributed-mode.html
- **Inline Map state** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-asl-use-map-state-inline-mode.html
- **ItemProcessor** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-asl-use-map-state.html#amazon-states-language-item-processor
- **ItemBatcher** — https://docs.aws.amazon.com/step-functions/latest/dg/batch-processing-item-batcher.html
- **Distributed Map S3 input** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-asl-use-map-state-distributed-mode.html#dist-map-s3-input
- **Parallel vs Map** — https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-parallel-state.html
- **Step Functions quotas** — https://docs.aws.amazon.com/step-functions/latest/dg/limits-overview.html
- **Step Functions pricing** — https://aws.amazon.com/step-functions/pricing/
