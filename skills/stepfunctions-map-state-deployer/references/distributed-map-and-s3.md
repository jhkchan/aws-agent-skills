# Distributed Map and S3 Input — Step Functions Map State Deployer

Deep reference on Distributed Map internals (child executions,
ExecutionType, Label, quota), S3 input via ItemReader/ReaderConfig
(CSV, JSON, JSONL), external input sources (Timestream, Firehose),
Parallel state vs Map state comparison, and the cost model. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Distributed Map internals

### Child executions

Each batch in a Distributed Map is a separate child execution. The
child execution:
- Has its own execution ARN
- Has its own execution history
- Is independently billed
- Counts against the account's concurrent execution quota

```text
Parent execution:
  └── ProcessRecords (Distributed Map, 100 batches)
        ├── Child execution 1 (batch 1, 100 items)
        ├── Child execution 2 (batch 2, 100 items)
        ├── ...
        └── Child execution 100 (batch 100, 100 items)

Each child:
  - Own ARN: arn:aws:states:...:execution:DataPipeline/<parent-id>:<label>-<batch-num>
  - Own history (does NOT grow parent's history)
  - Own billing (state transitions counted separately)
```

### ExecutionType

Distributed Map supports two ExecutionType values:

| ExecutionType | Billing | History | Max Duration |
|---|---|---|---|
| STANDARD | Per state transition | Retained for 90 days | Unlimited |
| EXPRESS | Per invocation + duration | At-least-once (async) | 5 minutes |

```json
{
  "ItemProcessor": {
    "ProcessorConfig": {
      "Mode": "DISTRIBUTED",
      "ExecutionType": "STANDARD"
    }
  }
}
```

**Key implication:** Express child executions are cheaper but have a
5-minute max duration. If a batch takes longer than 5 minutes, use
STANDARD.

### Label

The `Label` field customizes child execution naming for easier
identification.

```json
{
  "ProcessRecords": {
    "Type": "Map",
    "Label": "data-pipeline-batch",
    "ItemProcessor": {
      "ProcessorConfig": { "Mode": "DISTRIBUTED" },
      ...
    }
  }
}
```

Child executions are named: `<parent-execution-name>:<label>-<index>`

Without Label, child executions use a default naming scheme that is
harder to correlate with the parent.

### Quota summary

| Quota | Value | Adjustable |
|---|---|---|
| Max items per Map state run | 10000 | No |
| Max batches per Map state run | 10000 | No |
| Max concurrent child executions per Map state | 10000 | No |
| Account concurrent executions | 100000 | Yes |
| Max S3 object size | 30 GB | No |
| Max payload per batch | 64 KB (configurable) | Yes (up to 256 KB) |

## S3 input via ItemReader

### CSV input

```json
{
  "ProcessCSV": {
    "Type": "Map",
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
    "ItemProcessor": { ... }
  }
}
```

CSV rows are converted to JSON objects. If `CSVHeaderLocation` is
`FIRST_ROW`, the first row of the CSV is treated as column names.

```text
CSV file:
  id,name,value
  1,alpha,100
  2,beta,200
  3,gamma,300

Items passed to Map:
  [ {"id":"1","name":"alpha","value":"100"},
    {"id":"2","name":"beta","value":"200"},
    {"id":"3","name":"gamma","value":"300"} ]
```

### JSON input

```json
{
  "ItemReader": {
    "Resource": "arn:aws:states:::s3:getObject",
    "ReaderConfig": {
      "InputType": "JSON"
    },
    "Parameters": {
      "Bucket": "my-data-bucket",
      "Key": "datasets/records.json"
    }
  }
}
```

The S3 object must contain a JSON array. Each element becomes one item.

### JSONL input

```json
{
  "ItemReader": {
    "Resource": "arn:aws:states:::s3:getObject",
    "ReaderConfig": {
      "InputType": "JSONL"
    },
    "Parameters": {
      "Bucket": "my-data-bucket",
      "Key": "datasets/records.jsonl"
    }
  }
}
```

JSONL (JSON Lines) has one JSON object per line. Each line becomes one
item.

### S3 IAM permissions

The state machine role needs `s3:GetObject` on the target bucket/key:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-data-bucket/datasets/*"
    }
  ]
}
```

### S3 input with prefix filtering

Use `Prefix` in `ReaderConfig` to limit which S3 objects are read when
pointing at a bucket + prefix instead of a single key.

```json
{
  "ItemReader": {
    "Resource": "arn:aws:states:::s3:listObjectsV2",
    "ReaderConfig": {
      "InputType": "CSV"
    },
    "Parameters": {
      "Bucket": "my-data-bucket",
      "Prefix": "datasets/2026-08/"
    }
  }
}
```

This reads all CSV files under the prefix and concatenates them into
the item stream.

## External input sources

### Timestream as input (2024-2025)

Distributed Map can use Amazon Timestream query results as input. This
enables time-series data processing without pre-materializing into S3.

```json
{
  "ItemReader": {
    "Resource": "arn:aws:states:::timestream:query",
    "Parameters": {
      "QueryString": "SELECT * FROM my_database.my_table WHERE time > ago(1h)"
    },
    "ReaderConfig": {
      "InputType": "JSON"
    }
  }
}
```

The Timestream query result rows become Map state items.

**IAM requirement:** the state machine role needs
`timestream:Query` and `timestream:DescribeEndpoints`.

### Firehose as input (2024-2025)

Amazon Kinesis Data Firehose delivery streams can serve as input. This
enables near-real-time batch processing of streaming data.

```json
{
  "ItemReader": {
    "Resource": "arn:aws:states:::firehose:getRecord",
    "Parameters": {
      "DeliveryStreamName": "my-stream"
    },
    "ReaderConfig": {
      "InputType": "JSONL",
      "MaxItems": 5000
    }
  }
}
```

## Parallel state vs Map state

### When to use Parallel

Parallel state runs DIFFERENT branches concurrently. Each branch is a
distinct sub-workflow.

```text
Use Parallel when:
  ├── You need to run 3 different Tasks at the same time
  ├── Each branch does something different (e.g., send email + update DB + write log)
  ├── Branches are static (not driven by an input array)
  └── You need fan-out of heterogeneous operations
```

### When to use Map

Map state runs the SAME sub-workflow for each item in an array.

```text
Use Map when:
  ├── You have an array of items to process
  ├── Each item goes through the same workflow
  ├── The array size is dynamic (runtime input)
  └── You need fan-out of homogeneous operations
```

### Comparison table

| Feature | Parallel State | Map State |
|---|---|---|
| Branch definition | Multiple `Branches` (static) | Single `ItemProcessor` (per item) |
| Input | Same input to all branches | Each item from array |
| Output | Array of branch results | Array of iteration results |
| Dynamic items | No | Yes (array-driven) |
| Distributed mode | No | Yes (Distributed Map) |
| S3 input | No | Yes |
| Batch processing | No | Yes (ItemBatchSize/ItemBatcher) |
| Max branches/iterations | 25 branches | Inline: 5000, Distributed: 10000 |

## Cost model in detail

### Inline Map cost

Inline Map runs within the parent execution context. There is NO
additional cost beyond the parent execution's state transitions.

```text
Parent execution: 10 state transitions
  └── Inline Map: 5000 items × 3 state transitions each = 15000 transitions
Total: 10 + 15000 = 15010 state transitions
Billed: 15010 × $0.025/1000 = $0.375
```

The Map iterations are included in the parent's transition count. No
child executions are spawned.

### Distributed Map cost

Each batch is a separate child execution. Each child execution is
billed independently.

```text
Parent execution: 5 state transitions
  └── Distributed Map: 100 batches (ItemBatchSize 100)
        ├── Child execution 1: 3 state transitions
        ├── Child execution 2: 3 state transitions
        ├── ...
        └── Child execution 100: 3 state transitions
Total transitions: 5 + (100 × 3) = 305
Billed: 305 × $0.025/1000 = $0.007625

Compare: same 10000 items with ItemBatchSize 1:
  10000 child executions × 3 transitions = 30000 + 5 = 30005
  Billed: 30005 × $0.025/1000 = $0.75003
```

### Cost optimization strategies

1. **Use ItemBatchSize/ItemBatcher** to reduce child execution count.
   This is the single most impactful optimization.

2. **Use Inline Map** when item count is under 5000 and S3 input is
   not needed. No extra cost.

3. **Use Express ExecutionType** for short-lived batches (under 5
   minutes). Express billing is per-invocation + duration, which is
   cheaper for small batches.

4. **Limit MaxItems** when you do not need to process the entire
   dataset. Processing fewer items = fewer child executions.

5. **Use S3 input** instead of embedding large arrays in the execution
   input. S3 input avoids the 256KB execution input limit and is
   cheaper for large datasets.

## Step 5 - Distributed Map with S3 input (ItemReader template) (moved from SKILL.md)

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
