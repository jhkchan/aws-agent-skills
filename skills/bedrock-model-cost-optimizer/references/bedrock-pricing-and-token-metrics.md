# Bedrock Pricing and Token Metrics Reference

Supplementary reference for the Bedrock Model Cost Optimizer skill. Loaded
on-demand when detailed pricing math, CloudWatch metric queries, or
prompt caching / batch API setup is needed.

## Bedrock model pricing (us-east-1, 2026, USD)

### Claude family — per 1K tokens

| Model | Input $/1K | Output $/1K | Cache write $/1K | Cache read $/1K | Output/Input ratio |
|---|---|---|---|---|---|
| Claude Opus (claude-3-opus) | $0.01500 | $0.07500 | $0.01875 | $0.00150 | 5.0x |
| Claude Sonnet (claude-3-5-sonnet-v2) | $0.00300 | $0.01500 | $0.00375 | $0.00030 | 5.0x |
| Claude Haiku (claude-3-haiku) | $0.00025 | $0.00125 | $0.00031 | $0.000025 | 5.0x |

### Nova family — per 1K tokens

| Model | Input $/1K | Output $/1K | Output/Input ratio |
|---|---|---|---|
| Nova Pro | $0.00080 | $0.00320 | 4.0x |
| Nova Lite | $0.00006 | $0.00024 | 4.0x |
| Nova Micro | $0.000035 | $0.00014 | 4.0x |

### Embedding models — per 1K tokens

| Model | $/1K tokens | Notes |
|---|---|---|
| Titan Embed Text v2 | $0.00002 | Cheapest; 1024-dim default |
| Cohere Embed English v3 | $0.00010 | 1024-dim; higher quality |
| Cohere Embed Multilingual v3 | $0.00010 | 1024-dim; multilingual |

### Cost hierarchy summary

```
Per-token cost ranking (cheapest to most expensive):
  Nova Micro < Nova Lite < Haiku < Nova Pro < Sonnet < Opus

Haiku vs Opus:  60x cheaper (both input and output)
Haiku vs Sonnet: 12x cheaper (both input and output)
Nova Micro vs Haiku: ~7x cheaper on input, ~9x on output
```

### Batch inference discount

All models receive a 50% discount on both input and output token rates
when invoked via `CreateModelInvocationJob` (batch API):

```
Batch rate = on-demand rate × 0.50
```

### Guardrails pricing

| Component | Rate | Notes |
|---|---|---|
| Text processing (input or output) | $0.001/1K tokens | Charged per processed token |
| Apply to both input + output | 2× overhead | Narrow to output-only where possible |

### Provisioned throughput

Purchased in model units for a time commitment (1 hour to 1 month).
Contact AWS for a quote. Generally cost-effective when on-demand spend
exceeds $10,000/month with steady traffic (CV < 0.3).

## CloudWatch Bedrock metrics (AWS/Bedrock namespace)

### Key metrics for cost optimization

| Metric | Description | Unit | How to use |
|---|---|---|---|
| `InputTokenCount` | Total input tokens processed | Count (Sum) | Primary cost driver for input |
| `OutputTokenCount` | Total output tokens generated | Count (Sum) | Primary cost driver for output (3-5x input) |
| `InvocationCount` | Number of model invocations | Count (Sum) | Volume multiplier |
| `InvocationLatency` | End-to-end invocation latency | Milliseconds (Avg, p95) | Quality-of-service indicator |
| `ThrottledInvocationCount` | Invocations throttled | Count (Sum) | Throughput-limit signal |
| `CacheReadInputTokenCount` | Input tokens served from cache | Count (Sum) | Caching effectiveness |
| `CacheWriteInputTokenCount` | Input tokens written to cache | Count (Sum) | Cache population cost |

### CLI: pull token metrics for a model

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InputTokenCount \
  --dimensions Name=ModelId,Value=anthropic.claude-3-opus-20240229-v1:0 \
  --start-time $(date -u -d '-30 days' +%FT%TZ) \
  --end-time $(date -u +%FT%TZ) \
  --period 86400 \
  --statistics Sum \
  --output json
```

```bash
# Output tokens
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name OutputTokenCount \
  --dimensions Name=ModelId,Value=anthropic.claude-3-opus-20240229-v1:0 \
  --start-time $(date -u -d '-30 days' +%FT%TZ) \
  --end-time $(date -u +%FT%TZ) \
  --period 86400 \
  --statistics Sum \
  --output json
```

```bash
# Invocation count + latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InvocationCount \
  --dimensions Name=ModelId,Value=anthropic.claude-3-opus-20240229-v1:0 \
  --start-time $(date -u -d '-30 days' +%FT%TZ) \
  --end-time $(date -u +%FT%TZ) \
  --period 86400 \
  --statistics Sum Average \
  --output json
```

### CLI: Cost Explorer Bedrock spend

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-07-11,End=2026-08-11 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"Service","Values":["Amazon Bedrock"]}}' \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=UsageType \
  --output json
```

## Prompt caching setup

### Cache hit rate calculation

```
cache_hit_rate = CacheReadInputTokenCount / InputTokenCount

If cache_hit_rate > 0.50, caching is effective.
If cache_hit_rate < 0.10, caching may not be worth the write premium.
```

### Cache pricing math

```
Without caching:
  cost = input_tokens × input_rate

With caching (per invocation):
  cache_write cost = cached_tokens × input_rate × 1.25 (write premium)
  cache_read cost  = cached_tokens × input_rate × 0.10 (90% discount)

Break-even: cache must be hit > 2x within TTL to offset write premium.
```

### Application-layer configuration (Python SDK)

```python
import boto3, json

client = boto3.client('bedrock-runtime')

response = client.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": [
            {
                "type": "text",
                "text": "<lengthy system prompt repeated across invocations>",
                "cache_control": {"type": "ephemeral"}
            }
        ],
        "messages": [
            {"role": "user", "content": "<dynamic user query>"}
        ]
    })
)
```

### Prompt Management API

```bash
aws bedrock create-prompt \
  --name "cached-legal-analyser" \
  --default-variant '{
    "modelId": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "templateConfiguration": {
      "text": {
        "text": "System: {{system_prompt}}\n\nUser: {{user_query}}",
        "cachePoint": {"type": "ephemeral"}
      }
    }
  }'
```

## Batch inference API

### Create a batch job

```bash
aws bedrock create-model-invocation-job \
  --job-name "bulk-summarisation-2026-08" \
  --model-id "anthropic.claude-3-haiku-20240307-v1:0" \
  --input-data-config '{"s3InputDataConfig": {"s3Uri": "s3://my-bucket/input/"}}' \
  --output-data-config '{"s3OutputDataConfig": {"s3Uri": "s3://my-bucket/output/"}}' \
  --role-arn "arn:aws:iam::<acct>:role/BedrockBatchRole"
```

### Input format (JSONL in S3)

Each line is a separate invocation request:

```json
{"recordId": "1", "modelInput": {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 300, "messages": [{"role": "user", "content": "Summarise this document..."}]}}
{"recordId": "2", "modelInput": {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 300, "messages": [{"role": "user", "content": "Summarise this document..."}]}}
```

### Monitor batch job

```bash
aws bedrock get-model-invocation-job --job-identifier <job-id>
aws bedrock list-model-invocation-jobs --status-contains Completed
```

### Batch cost calculation

```
batch_cost = (input_tokens × input_rate × 0.50) + (output_tokens × output_rate × 0.50)
```

## Fine-tuning cost estimate

```bash
aws bedrock create-model-customization-job \
  --job-name "fine-tune-haiku-support" \
  --base-model-identifier "anthropic.claude-3-haiku-20240307-v1:0" \
  --customization-type FINE_TUNING \
  --training-data-config '{"s3Uri": "s3://bucket/training-data.jsonl"}' \
  --output-data-config '{"s3Uri": "s3://bucket/output/"}' \
  --hyper-parameters '{"epochCount": "3", "batchSize": "32", "learningRate": "0.001"}'
```

Training cost: per-hour compute on the training instance + per-token
processing of training data. Typically $50-$500 per fine-tuning run
depending on dataset size and model.

## Regional pricing multipliers

Approximate multiplier vs us-east-1.

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| eu-west-1, eu-central-1 | 1.10x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10x | |
| ap-south-1 (Mumbai) | 1.15x | |

Always re-check via the AWS Pricing API for production estimates.

## Cost calculation worked examples

### Example 1: Opus-to-Haiku downgrade

```
Workload: FAQ chatbot
Current: Opus, 500M input tokens, 36M output tokens, 200k invocations
Projected: Haiku, same token counts

Current monthly:
  input:  500,000,000 / 1000 × $0.015 = $7,500.00
  output: 36,000,000 / 1000 × $0.075 = $2,700.00
  total: $10,200.00

Projected monthly (Haiku):
  input:  500,000,000 / 1000 × $0.00025 = $125.00
  output: 36,000,000 / 1000 × $0.00125 = $45.00
  total: $170.00

Monthly saving: $10,030.00 (98.3%)
```

### Example 2: Prompt caching

```
Workload: Legal analyser on Sonnet
System prompt: 2,800 tokens, 60,000 invocations/month
Without caching:
  2,800 × 60,000 / 1000 × $0.003 = $504.00/month on system prompt alone
With caching (90% hit rate, ~12,000 cache writes):
  cache write: 2,800 × 12,000 / 1000 × $0.00375 = $126.00
  cache read:  2,800 × 48,000 / 1000 × $0.00030 = $40.32
  total: $166.32/month
  Saving: $337.68/month (67%) on the cached portion
```

### Example 3: Batch migration

```
Workload: Bulk summarisation on Haiku
750M input tokens, 250M output tokens, 500k invocations
Real-time cost:
  750M / 1000 × $0.00025 = $187.50
  250M / 1000 × $0.00125 = $312.50
  total: $500.00
Batch cost (50% discount):
  $187.50 × 0.50 = $93.75
  $312.50 × 0.50 = $156.25
  total: $250.00
  Saving: $250.00/month (50%)
```

## Pre-flight data sources (required metrics and CLI) (moved from SKILL.md)

**Required data sources** (summarized — see reference for full CLI):
1. Model list and access: `aws bedrock list-foundation-models`
2. InputTokenCount + OutputTokenCount (14-30 day window): `aws cloudwatch get-metric-statistics --namespace AWS/Bedrock`
3. InvocationCount + InvocationLatency: same namespace
4. Cost Explorer spend: `aws ce get-cost-and-usage --filter Service=Bedrock`
5. Prompt caching config: `aws bedrock get-prompt` or inspect application code
6. Guardrails: `aws bedrock list-guardrails`, `aws bedrock get-guardrail`
7. Batch jobs: `aws bedrock list-model-invocation-jobs`

## Model cost hierarchy (per-1K token pricing) (moved from SKILL.md)

**Model cost hierarchy (us-east-1, 2026, approximate per 1K tokens):**

```
Input token pricing (per 1K tokens):
  Claude Opus:       $0.01500
  Claude Sonnet:     $0.00300
  Claude Haiku:      $0.00025
  Nova Pro:          $0.00080
  Nova Lite:         $0.00006
  Nova Micro:        $0.000035

Output token pricing (per 1K tokens):
  Claude Opus:       $0.07500
  Claude Sonnet:     $0.01500
  Claude Haiku:      $0.00125
  Nova Pro:          $0.00320
  Nova Lite:         $0.00024
  Nova Micro:        $0.00014

Ratio (Haiku vs Opus):
  Input:  $0.00025 / $0.01500 = 60x cheaper
  Output: $0.00125 / $0.07500 = 60x cheaper
```

## Prompt caching pricing math (moved from SKILL.md)

**Pricing math:**
```
Without caching:
  cached_portion_tokens × $input_rate_per_1k / 1000 × invocations_per_month

With caching (assuming 90% cache hit rate):
  First write: cached_portion_tokens × $input_rate × 1.25 (write premium) × cache_writes_per_month
  Cache hits: cached_portion_tokens × $input_rate × 0.10 × cache_hits_per_month

Example: 2,000-token system prompt, 1M invocations/month, Claude Sonnet ($0.003/1k input):
  Without:   2,000 × $0.003/1000 × 1,000,000 = $6,000/month
  With:      write: 2,000 × $0.003/1000 × 1.25 × ~12,000 (cache writes) = $90/month
             hits:  2,000 × $0.003/1000 × 0.10 × 988,000 = $592/month
             total: ~$682/month
  Saving:    $5,318/month (89%)
```

## CLI to enable prompt caching (moved from SKILL.md)

**CLI to enable prompt caching:**

Prompt caching is configured at the application layer by setting the
`cache_point` in the invoke request. Via the AWS SDK:

```python
import boto3
client = boto3.client('bedrock-runtime')
response = client.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": [
            {
                "type": "text",
                "text": "<2,000-token system prompt>",
                "cache_control": {"type": "ephemeral"}
            }
        ],
        "messages": [{"role": "user", "content": "query"}]
    })
)
```

Or via Bedrock Prompt Management:

```bash
aws bedrock create-prompt \
  --name "cached-support-bot" \
  --default-variant '{"modelId": "anthropic.claude-3-5-sonnet-20241022-v2:0", ...}'
```

## Batch inference pricing and CLI (moved from SKILL.md)

**Pricing comparison:**
```
Real-time InvokeModel:
  input_tokens × $input_rate + output_tokens × $output_rate

Batch (CreateModelInvocationJob):
  input_tokens × $input_rate × 0.50 + output_tokens × $output_rate × 0.50
  (50% discount on both input and output)
```

**CLI to create a batch job:**
```bash
aws bedrock create-model-invocation-job \
  --job-name "bulk-summarisation" \
  --model-id "anthropic.claude-3-haiku-20240307-v1:0" \
  --input-data-config '{"s3InputDataConfig": {"s3Uri": "s3://my-bucket/input/"}}' \
  --output-data-config '{"s3OutputDataConfig": {"s3Uri": "s3://my-bucket/output/"}}'
```

## Fine-tuning vs few-shot break-even analysis (moved from SKILL.md)

**Break-even analysis:**
```
Few-shot cost (monthly):
  few_shot_tokens × $input_rate × invocations_per_month

Fine-tune cost (one-time):
  training_job_hours × $training_rate_per_hour + training_tokens × $training_token_rate

Fine-tune serving cost (monthly):
  fine_tuned_model_input_rate × invocations_per_month
  (typically same as base model rate; fine-tuned models do NOT cost more per token on Bedrock)

Break-even month = fine_tune_one_time_cost / (few_shot_monthly_cost - fine_tune_serving_monthly_cost)
```

## Guardrails cost model (moved from SKILL.md)

**Guardrails cost model:**
```
Per invocation: guardrail processes input and/or output tokens.
Guardrail rate (us-east-1, 2026): ~$0.001/1k tokens processed

If applied to BOTH input and output:
  overhead = (input_tokens + output_tokens) × $0.001/1k

If applied to OUTPUT ONLY:
  overhead = output_tokens × $0.001/1k (50% reduction)
```

## Knowledge Base cost model (moved from SKILL.md)

**Knowledge Base cost model:**
```
Per query: embedding_cost + vector_store_query_cost + model_invocation_cost

OpenSearch Serverless OCU: ~$400/month minimum (0.5 ingestion + 0.5 search)
  < 10k queries/month: OCU dominates → consider Pinecone or Neptune Analytics
  > 100k queries/month: model invocation dominates → OCU amortised
```
