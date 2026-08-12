# Map Configuration and Batching — Step Functions Map State Deployer

Deep reference on Map state configuration fields (ItemsPath,
MaxConcurrency, MaxItems, ItemBatchSize, ItemBatcher), ItemProcessor
vs Iterator semantics, batch processing mechanics, and common
configuration pitfalls. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays scannable.

## Map state configuration fields

### ItemsPath

`ItemsPath` specifies where in the input to find the array to iterate
over. It uses JSONPath syntax.

```json
{
  "ProcessOrders": {
    "Type": "Map",
    "ItemsPath": "$.orders",
    "ItemProcessor": { ... }
  }
}
```

If `ItemsPath` is omitted, the entire state input is treated as the
array. If the input is not a JSON array, the Map state fails.

```text
Input: { "orders": [1, 2, 3], "metadata": { ... } }
ItemsPath: "$.orders" → iterates over [1, 2, 3]

Input: [1, 2, 3]
ItemsPath: null → iterates over [1, 2, 3]

Input: { "name": "test" }
ItemsPath: null → FAILS (input is not an array)
```

### MaxConcurrency vs MaxConcurrencyPath

`MaxConcurrency` is a static value. `MaxConcurrencyPath` is a
JSONPath that references a value in the input at runtime.

```json
{
  "ProcessItems": {
    "Type": "Map",
    "MaxConcurrencyPath": "$.concurrency"
  }
}
```

If the input is `{ "items": [1,2,3], "concurrency": 5 }`, then
MaxConcurrency is 5 at runtime.

**Limits:**
- Inline Map: MaxConcurrency max 40
- Distributed Map: MaxConcurrency max 1000

If the value exceeds the max, it is silently capped.

### MaxItems / MaxItemsPath

Only supported on Distributed Map. Caps the number of items processed.

```json
{
  "ProcessCSV": {
    "Type": "Map",
    "MaxItems": 10000,
    "ItemProcessor": {
      "ProcessorConfig": { "Mode": "DISTRIBUTED" },
      ...
    }
  }
}
```

Setting MaxItems on Inline Map is silently ignored — no error, no cap.

## ItemProcessor vs Iterator

### Field comparison

| Feature | Iterator (legacy) | ItemProcessor (current) |
|---|---|---|
| Introduced | Original Step Functions | September 2022 |
| Inline Map | Yes | Yes (Mode: INLINE) |
| Distributed Map | No | Yes (Mode: DISTRIBUTED) |
| ProcessorConfig | Not available | Available |
| ExecutionType | Not available | STANDARD or EXPRESS |
| Status | Deprecated (still functional) | Recommended |

### Migration from Iterator to ItemProcessor

```text
Before (Iterator — Inline only):
  "Map": {
    "Type": "Map",
    "Iterator": {
      "StartAt": "...",
      "States": { ... }
    }
  }

After (ItemProcessor — Inline):
  "Map": {
    "Type": "Map",
    "ItemProcessor": {
      "ProcessorConfig": { "Mode": "INLINE" },
      "StartAt": "...",
      "States": { ... }
    }
  }

After (ItemProcessor — Distributed):
  "Map": {
    "Type": "Map",
    "ItemProcessor": {
      "ProcessorConfig": {
        "Mode": "DISTRIBUTED",
        "ExecutionType": "STANDARD"
      },
      "StartAt": "...",
      "States": { ... }
    }
  }
```

### Why Iterator forces Inline mode

The `Iterator` field predates Distributed Map. Step Functions treats
any Map state using `Iterator` as Inline — even if a `ProcessorConfig`
block is present, it is ignored. To use Distributed Map, you MUST
switch to `ItemProcessor`.

## Batch processing

### ItemBatchSize (simple batching)

Groups items into fixed-size batches. Each batch becomes one child
execution in Distributed Map.

```json
{
  "ProcessItems": {
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
}
```

With 10000 items and ItemBatchSize 100:
- 100 child executions (10000 / 100)
- Each child receives a JSON array of 100 items

### ItemBatcher (advanced batching)

Provides additional control beyond ItemBatchSize.

```json
{
  "ProcessItems": {
    "Type": "Map",
    "ItemBatcher": {
      "MaxItemsPerBatch": 100,
      "MaxInputBytesPerBatch": 1048576,
      "BatchInput": {
        "pipeline": "production",
        "run_date": "2026-08-11"
      }
    },
    "ItemProcessor": { ... }
  }
}
```

| Field | Description | Default |
|---|---|---|
| MaxItemsPerBatch | Max items grouped per batch | — (required) |
| MaxInputBytesPerBatch | Max payload size per batch in bytes | 65536 (64 KB) |
| BatchInput | Extra JSON context merged into each batch | None |

### ItemBatchSize vs ItemBatcher

- **Mutually exclusive.** Use ONE, not both.
- **ItemBatchSize** for simple fixed-size batches.
- **ItemBatcher** when you need MaxInputBytesPerBatch control or
  BatchInput injection.

### What the ItemProcessor receives

When ItemBatchSize or ItemBatcher is set, the ItemProcessor
sub-workflow receives:

```json
[
  { "itemId": 1, "name": "alpha" },
  { "itemId": 2, "name": "beta" },
  { "itemId": 3, "name": "gamma" }
]
```

A JSON ARRAY of items, not a single item. The Lambda or Task must
iterate within the batch.

### Batching without a nested Map

For simple batch processing, use a Lambda that receives the array:

```python
import boto3

def lambda_handler(event, context):
    # event is a JSON array of items
    results = []
    for item in event:
        result = process_item(item)
        results.append(result)
    return { "batch_results": results }
```

## ToleratedFailureCount and ToleratedFailurePercentage

Only for Distributed Map. Controls partial failure tolerance.

```json
{
  "ProcessItems": {
    "Type": "Map",
    "ToleratedFailureCount": 10,
    "ToleratedFailurePercentage": 5,
    "ItemProcessor": { ... }
  }
}
```

- If EITHER threshold is exceeded, the Map state fails.
- Both can be set simultaneously.
- Default for both is 0 (no failures tolerated).

**Failure counting:** a "failure" is a child execution that fails (not
an individual item). With ItemBatchSize 100, one failed batch counts
as one failure (even though 100 items were in it).

## ItemSelector

Transforms the input before passing to each iteration.

```json
{
  "ProcessItems": {
    "Type": "Map",
    "ItemSelector": {
      "item.$": "$$.Map.Item.Value",
      "index.$": "$$.Map.Item.Index",
      "pipeline": "production"
    },
    "ItemProcessor": { ... }
  }
}
```

Each iteration receives `{ "item": <value>, "index": <n>, "pipeline": "production" }`
instead of the raw item value. This is useful for adding static
context to each iteration.

## Common configuration pitfalls

### Pitfall 1: MaxConcurrency: 0 means unlimited

A common mistake is setting `MaxConcurrency: 0` expecting sequential
processing. Zero means UNLIMITED concurrency.

```text
MaxConcurrency: 0  → unlimited (all items run in parallel)
MaxConcurrency: 1  → sequential (one at a time)
MaxConcurrency: 10 → up to 10 in parallel
```

### Pitfall 2: ItemBatchSize on Inline Map

ItemBatchSize is silently ignored on Inline Map. If you need batching,
switch to Distributed Map.

### Pitfall 3: Iterator with ProcessorConfig

Using `Iterator` with `ProcessorConfig: { Mode: "DISTRIBUTED" }` does
NOT enable Distributed Map. The Iterator field forces Inline mode.
Switch to ItemProcessor.

### Pitfall 4: MaxItems on Inline Map

MaxItems is silently ignored on Inline Map. If you need an item cap,
switch to Distributed Map.

## Terraform example

```hcl
resource "aws_sfn_state_machine" "data_pipeline" {
  name     = "DataPipeline"
  role_arn = aws_iam_role.sfn.arn

  definition = jsonencode({
    StartAt = "ProcessRecords"
    States = {
      ProcessRecords = {
        Type           = "Map"
        MaxConcurrency = 50
        ItemBatchSize  = 100
        ToleratedFailurePercentage = 5

        ItemReader = {
          Resource = "arn:aws:states:::s3:getObject"
          ReaderConfig = {
            InputType         = "CSV"
            CSVHeaderLocation = "FIRST_ROW"
          }
          Parameters = {
            Bucket = "my-data-bucket"
            Key    = "datasets/records.csv"
          }
        }

        ItemProcessor = {
          ProcessorConfig = {
            Mode          = "DISTRIBUTED"
            ExecutionType = "STANDARD"
          }
          StartAt = "ProcessRow"
          States = {
            ProcessRow = {
              Type     = "Task"
              Resource = aws_lambda_function.process_row.arn
              End      = true
            }
          }
        }
      }
    }
  })
}
```
