# Lambda Pricing and Power Tuning Reference

Supplementary reference for the Lambda Cost Optimizer skill. Loaded on-demand
when detailed pricing math, Power Tuning deployment steps, or runtime
compatibility matrices are needed.

## Lambda pricing (us-east-1, 2026, USD)

### Request pricing

| Pricing model | $/request | Notes |
|---|---|---|
| On-demand | $0.0000002 (0.00002 cents) | First 1M requests/month free tier |
| Provisioned concurrency requests | $0.00005 | Charged IN ADDITION to provisioned compute; 250× more expensive than on-demand per request |

### Compute pricing ($/GB-second)

| Pricing model | $/GB-second | Idle charge? | Notes |
|---|---|---|---|
| On-demand | $0.0000166667 | No | Pay only for execution time |
| Provisioned concurrency | $0.000015 | YES — bills for full provisioned window | Slightly cheaper per GB-second but pays for idle |

### Free tier

- 1,000,000 requests/month free (on-demand only)
- 400,000 GB-seconds/month free (on-demand only)
- Provisioned concurrency is NOT included in the free tier

### Duration billing precision

Lambda bills duration in 1 ms increments (since 2021). Previously billed
in 100 ms increments — the change made sub-100ms functions significantly
cheaper. Always report duration in milliseconds for precision.

## Memory-to-CPU mapping

| Memory (MB) | vCPU (fractional) | Notes |
|---|---|---|
| 128 | ~0.07 vCPU | Minimum; very slow for CPU-bound workloads |
| 256 | ~0.14 vCPU | |
| 512 | ~0.29 vCPU | |
| 1024 | ~0.58 vCPU | |
| 1769 | 1.0 vCPU | Full vCPU threshold |
| 2048 | ~1.16 vCPU | |
| 3072 | ~1.74 vCPU | |
| 3538 | 2.0 vCPU | 2 full vCPUs |
| 5120 | ~2.89 vCPU | |
| 6144 | ~3.47 vCPU | |
| 8192 | ~4.63 vCPU | |
| 10240 | 10 GB | ~5.79 vCPU |
| 10240 (max) | 10 GB | Maximum memory |

The CPU-memory ratio is LINEAR. The inflection point at 1769 MB matters
because Lambda's scheduler allocates full vCPU slices at that boundary —
CPU-bound workloads see step-function improvements there.

## Power Tuning deployment guide

### Deploy via Serverless Application Repository (SAR)

```bash
# Create the change set (one-time)
aws serverlessrepo create-cloudformation-change-set \
  --application-id arn:aws:serverlessrepo:us-east-1:451482290155:XfE9cVlKBl \
  --stack-name serverlessrepo-lambda-power-tuning \
  --capabilities CAPABILITY_IAM

# Note the ChangeSetId from the response, then execute:
aws cloudformation execute-change-set \
  --change-set-name <ChangeSetId>

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name serverlessrepo-lambda-power-tuning

# Get the state machine ARN
aws cloudformation describe-stacks \
  --stack-name serverlessrepo-lambda-power-tuning \
  --query 'Stacks[0].Outputs[?OutputKey==`powerTuningStateMachineARN`].OutputValue' \
  --output text
```

### Power Tuning input schema

```json
{
  "lambda": {
    "resource": "arn:aws:lambda:us-east-1:<acct>:function:<name>",
    "payload": {},
    "num": 50,
    "enabled": true,
    "parallelInvocation": true,
    "query": "your-query-string"
  },
  "power": {
    "values": [128, 256, 512, 1024, 2048, 3008],
    "payload": {},
    "num": 5,
    "parallelInvocation": false
  },
  "optimize": "cost",
  "visualization": "auto"
}
```

| Field | Description | Default |
|---|---|---|
| `lambda.resource` | Function ARN to test | Required |
| `lambda.payload` | Test payload (JSON) | `{}` |
| `lambda.num` | Invocations per memory setting | 5 |
| `lambda.parallelInvocation` | Parallel (true) vs sequential (false) | false |
| `power.values` | Memory settings to test (MB) | [128, 256, 512, 1024, 2048, 3008, 5120] |
| `optimize` | "cost" or "speed" or "balanced" | "cost" |

### Interpreting Power Tuning output

```json
{
  "results": {
    "power": 512,
    "cost": 0.000000667,
    "duration": 1.02,
    "stateMachine": {
      "executionCost": 0.0000014
    },
    "lambdaPowerURL": "https://lambda-power-tuning.show/#<base64>"
  },
  "strategy": "cost"
}
```

| Field | Meaning | How to use |
|---|---|---|
| `power` | Cost-optimal memory setting | Compare to current `MemorySize` |
| `cost` | Cost per invocation at optimal | Multiply by monthly invocations for monthly cost |
| `duration` | Duration at optimal (seconds) | Compare to current p95 for latency impact |
| `stateMachine.executionCost` | Cost of the Power Tuning run | Typically $0.01-0.50; negligible vs savings |
| `lambdaPowerURL` | Visualization URL | Share with operator for transparency |

## Runtime ARM64 compatibility matrix

| Runtime | ARM64 support | Migration risk | Notes |
|---|---|---|---|
| nodejs20.x, nodejs18.x | Full | LOW | Change `--architectures arm64` |
| python3.12, python3.11 | Full | LOW | Verify C-extension deps have aarch64 wheels |
| java21 (Corretto), java17 | Full | LOW-MEDIUM | Verify JNI/native libs; SnapStart compatible |
| dotnet8 | Full | MEDIUM | Verify native deps |
| provided.al2023 | Full | MEDIUM | Recompile custom runtime for aarch64 |
| go1.x | Full | LOW | Recompile with `GOARCH=arm64` |
| ruby3.2 | Full | LOW | Verify native gem extensions |

## Event Source Mapping limits

| Source | Default batch size | Max batch size | Max batching window |
|---|---|---|---|
| SQS | 10 | 10000 | 300 seconds |
| Kinesis Data Streams | 10 | 10000 | 300 seconds |
| DynamoDB Streams | 10 | 10000 | 300 seconds |
| Amazon MSK (Kafka) | 10 | 10000 | 300 seconds |
| Amazon MQ | 10 | 10000 | 300 seconds |
| Self-managed Kafka | 10 | 10000 | 300 seconds |

## Common duration baselines by runtime

These are approximate "healthy" durations for common workload patterns.
Use as a sanity check, not a strict threshold.

| Workload | Runtime | Expected avg duration | Concerning avg duration |
|---|---|---|---|
| Simple API proxy | Node.js | 5-50 ms | > 200 ms |
| Simple API proxy | Python | 10-80 ms | > 300 ms |
| SQS message processor | Node.js | 50-200 ms | > 1 s |
| DB query + transform | Python | 100-500 ms | > 2 s |
| Image resize | Node.js/Python | 500-3000 ms | > 10 s |
| Java cold start (no SnapStart) | Java | 2-5 s init | > 8 s init |
| Java warm invocation | Java | 50-500 ms | > 2 s |
| ML inference | Python | 500-5000 ms | > 15 s (timeout risk) |

## Regional pricing multipliers

Approximate multiplier vs us-east-1 for Lambda compute and request rates.

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| us-west-1 | 1.05x | Slight premium |
| eu-west-1, eu-west-2, eu-central-1 | 1.10-1.15x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10-1.15x | |
| ap-south-1 (Mumbai) | 1.15-1.25x | |
| sa-east-1 (São Paulo) | 1.35-1.50x | Highest premium |
| af-south-1 (Cape Town) | 1.30-1.45x | |

Always re-check via the AWS Pricing API for production estimates.

## Cost calculation worked examples

### Example 1: Simple API proxy (low volume)

```
Function: api-auth-check
Memory: 128 MB (0.125 GB)
Average duration: 25 ms (0.025 s)
Monthly invocations: 10,000,000
Region: us-east-1

Monthly compute cost:
  10,000,000 × 0.025 × 0.125 × $0.0000166667 = $0.52

Monthly request cost:
  10,000,000 × $0.0000002 = $2.00

Total: $2.52/month
```

### Example 2: High-volume SQS processor

```
Function: sqs-event-normalizer
Memory: 512 MB (0.5 GB)
Average duration: 180 ms (0.18 s)
Monthly invocations: 800,000,000
Region: us-east-1

Monthly compute cost:
  800,000,000 × 0.18 × 0.5 × $0.0000166667 = $1,200.00

Monthly request cost:
  800,000,000 × $0.0000002 = $160.00

Total: $1,360.00/month

Optimization: increase batch size from 10 to 500
  New invocations: 800,000,000 / 50 = 16,000,000
  New duration (estimate, scales sublinearly): 180 ms × 3 = 540 ms (0.54 s)

New monthly compute: 16,000,000 × 0.54 × 0.5 × $0.0000166667 = $72.00
New monthly requests: 16,000,000 × $0.0000002 = $3.20
New total: $75.20/month
Saving: $1,284.80/month (94%)
```

### Example 3: Provisioned concurrency idle waste

```
Function: latency-sensitive-api
Memory: 1024 MB (1 GB)
Provisioned concurrency: 20
Actual traffic: avg 5 concurrent, p99 8 concurrent
Region: us-east-1

Provisioned compute cost (IDLE portion):
  Idle concurrent: 20 - 8 (p99) = 12 idle executions
  12 × 1 GB × 730 hours × 3600 s/h × $0.000015 = $946.08/month wasted on idle

Right-sizing to 10 provisioned:
  Idle concurrent: 10 - 8 = 2 idle
  2 × 1 GB × 730 × 3600 × $0.000015 = $78.84/month wasted on idle
  Saving: $867.24/month
```
