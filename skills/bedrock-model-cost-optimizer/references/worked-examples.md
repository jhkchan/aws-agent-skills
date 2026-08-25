# Worked Examples — Bedrock Model Cost Optimizer

Full worked examples covering Opus-to-Haiku downgrade with caching,
prompt caching enable, batch migration, response length control,
already-optimal, NEED_MORE_INFO, and an end-to-end optimisation
walkthrough. Loaded on demand — kept out of the main SKILL.md body so
the procedure stays scannable.

## Worked example — Opus-to-Haiku downgrade + prompt caching

```text
TARGET: anthropic.claude-3-opus-20240229-v1:0 (customer-support-bot)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Customer support chatbot using Opus for simple FAQ Q&A. Average
  output is 180 tokens (extraction/lookup), well within Haiku's
  capability. Downgrading to Haiku reduces per-token cost 60x on both
  input and output. Additionally, the 2,000-token system prompt is
  repeated on every invocation and prompt caching is not enabled,
  adding a further 89% saving on the cached portion.
RECOMMENDATION:
  Current: Opus, 2,500 input tokens/invocation, 180 output tokens/invocation, 200,000 invocations/month
  Proposed: Haiku, 2,500 input tokens/invocation (2,000 cached), 180 output tokens/invocation, 200,000 invocations/month
  Dimensions changed: model (Step 1) + caching (Step 2)
  Dimensions checked: model → (Opus to Haiku)  caching → (enable)
    batch ✓ (interactive, not eligible)  response_length ✓ (already concise)
    fine_tune ✓ (invocations too low to justify)  guardrails ✓ (none configured)
    throughput ✓ (spend below $10k threshold)
  Confidence: HIGH — FAQ Q&A is Haiku's sweet spot; output < 200 tokens
    confirms no complex generation; system prompt is static and repeated.
ESTIMATED_SAVINGS:
  Current monthly: $10,200.00
    input tokens: 500,000,000 × $0.015/1k = $7,500.00
    output tokens: 36,000,000 × $0.075/1k = $2,700.00
  Projected monthly: $147.50
    input tokens: 500,000,000 × $0.00025/1k = $125.00
    output tokens: 36,000,000 × $0.00125/1k = $45.00
    caching overhead: ~$22.50 (cache write premium + residual)
  Monthly saving: $10,052.50
    ($10,200.00 − $147.50 = $10,052.50)
  Annual saving: $120,630.00
MIGRATION_STEPS:
  1. Test Haiku on 100 representative FAQ queries; compare to Opus baseline:
     aws bedrock create-evaluation-job --model-identifiers ...
  2. Enable prompt caching: add "cache_control": {"type": "ephemeral"}
     to the system prompt block in the invoke call.
  3. Deploy Haiku behind a feature flag; route 10% traffic for 7 days.
  4. If quality holds, cut over 100% to Haiku.
CONFIRM: About to downgrade customer-support-bot from Opus to Haiku
  and enable prompt caching. Monthly saving $10,052.50 (98.6%). Proceed? (yes/no)
```

## Worked example — prompt caching enable (Sonnet, no model change)

```text
TARGET: anthropic.claude-3-5-sonnet-20241022-v2:0 (legal-analyser)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Legal document analyser using Sonnet with a 2,800-token system
  prompt repeated on every invocation. Prompt caching is not enabled.
  At ~2 invocations/sec, cache hit rate will exceed 90%. The cached
  portion drops from $0.003/1k to $0.00030/1k (90% reduction on cached
  tokens). Model is appropriate (Sonnet for reasoning); no downgrade.
RECOMMENDATION:
  Current: Sonnet, 3,000 input tokens/invocation (2,800 system + 200 user), no caching
  Proposed: Sonnet, 3,000 input tokens/invocation (2,800 cached), caching enabled
  Dimensions changed: caching (Step 2)
  Dimensions checked: model ✓ (Sonnet appropriate for legal reasoning)
    caching → (enable)  batch ✓ (interactive, not eligible)
    response_length ✓ (500 tokens reasonable)  fine_tune ✓ (invocations low)
    guardrails ✓ (none configured)  throughput ✓ (spend below threshold)
  Confidence: HIGH — invocation rate 2/sec ensures cache stays warm;
    system prompt is static; 90% hit rate projected.
ESTIMATED_SAVINGS:
  Current monthly: $990.00
    input: 180,000,000 × $0.003/1k = $540.00
    output: 30,000,000 × $0.015/1k = $450.00
  Projected monthly: $652.32
    input (non-cached): 12,000,000 × $0.003/1k = $36.00 (user queries)
    input (cache write): 2,800 × ~12,000 writes / 1k × $0.00375 = $126.00
    input (cache read): 2,800 × 48,000 / 1k × $0.00030 = $40.32
    output: 30,000,000 × $0.015/1k = $450.00 (unchanged)
    total: $652.32
  Monthly saving: $337.68 (34.1%)
  Annual saving: $4,052.16
MIGRATION_STEPS:
  1. Add cache_control to the system prompt block:
     "system": [{"type":"text","text":"<legal instructions>",
     "cache_control":{"type":"ephemeral"}}]
  2. Deploy and monitor CacheReadInputTokenCount for 7 days.
  3. Verify cache hit rate > 80%.
CONFIRM: About to enable prompt caching on legal-analyser. Monthly saving
  $337.68 (34.1%). No model change. Proceed? (yes/no)
```

## Worked example — batch inference migration

```text
TARGET: anthropic.claude-3-haiku-20240307-v1:0 (bulk-summariser)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Bulk document summarisation workload processing 500,000
  documents/month via real-time InvokeModel. Results are consumed by a
  nightly indexing pipeline — no user waiting. Batch API gives 50%
  discount on both input and output. Also resolves throttling (2.4%
  ThrottledInvocationCount).
RECOMMENDATION:
  Current: Haiku, real-time InvokeModel, 500,000 invocations/month
  Proposed: Haiku, Batch API, 500,000 invocations/month
  Dimensions changed: batch (Step 3)
  Dimensions checked: model ✓ (already on Haiku)  caching ✓ (input varies per doc)
    batch → (migrate)  response_length ✓ (500 tokens appropriate)
    fine_tune ✓ (not applicable)  guardrails ✓ (none)
    throughput ✓ (batch resolves throttling without provisioned commitment)
  Confidence: HIGH — workload is non-interactive; nightly SLA tolerates
    hours of batch processing; S3 I/O is straightforward.
ESTIMATED_SAVINGS:
  Current monthly: $500.00
    input: 750,000,000 × $0.00025/1k = $187.50
    output: 250,000,000 × $0.00125/1k = $312.50
  Projected monthly: $250.00
    input: $187.50 × 0.50 = $93.75
    output: $312.50 × 0.50 = $156.25
  Monthly saving: $250.00 (50%)
  Annual saving: $3,000.00
MIGRATION_STEPS:
  1. Prepare input JSONL in S3 (one line per document):
     s3://my-bucket/input/summarisation-2026-08.jsonl
  2. Create the batch job:
     aws bedrock create-model-invocation-job --job-name "nightly-summarisation"
       --model-id "anthropic.claude-3-haiku-20240307-v1:0"
       --input-data-config '{"s3InputDataConfig":{"s3Uri":"s3://my-bucket/input/"}}'
       --output-data-config '{"s3OutputDataConfig":{"s3Uri":"s3://my-bucket/output/"}}'
  3. Monitor: aws bedrock get-model-invocation-job --job-identifier <job-id>
  4. Wire the output S3 bucket to the search indexing pipeline.
CONFIRM: About to migrate bulk-summariser from real-time to Batch API.
  Monthly saving $250.00 (50%). Completion SLA: hours (overnight). Proceed? (yes/no)
```

## Worked example — response length control

```text
TARGET: anthropic.claude-3-5-sonnet-20241022-v2:0 (product-desc-gen)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Product description generator outputs avg 1,200 tokens where
  structured 300-token JSON would suffice. max_tokens is not set. Output
  tokens cost 5x more than input ($0.015/1k vs $0.003/1k for Sonnet).
  Setting max_tokens=300 and switching to JSON output reduces output
  cost by ~75%.
RECOMMENDATION:
  Current: Sonnet, 800 input tokens, 1,200 output tokens/invocation, no max_tokens
  Proposed: Sonnet, 800 input tokens, 300 output tokens/invocation, max_tokens=300 + JSON format
  Dimensions changed: response_length (Step 4)
  Dimensions checked: model ✓ (Sonnet appropriate for creative generation)
    caching ✓ (input varies per product)  batch ✓ (interactive e-commerce, not eligible)
    response_length → (max_tokens + structured output)
    fine_tune ✓ (invocations moderate)  guardrails ✓ (none)  throughput ✓ (spend below threshold)
  Confidence: HIGH — product descriptions in JSON are well-established;
    300 tokens is sufficient for title + description + attributes.
ESTIMATED_SAVINGS:
  Current monthly: $2,040.00
    input: 80,000,000 × $0.003/1k = $240.00
    output: 120,000,000 × $0.015/1k = $1,800.00
  Projected monthly: $660.00
    input: 80,000,000 × $0.003/1k = $240.00 (unchanged)
    output: 30,000,000 × $0.015/1k = $450.00 (75% reduction)
    total: $690.00
  Monthly saving: $1,350.00 (66.2%)
  Annual saving: $16,200.00
MIGRATION_STEPS:
  1. Set max_tokens=300 in the invoke body.
  2. Update system prompt: "Respond in JSON format: {title, description, attributes}."
  3. Add a stop sequence for "}" to ensure clean JSON termination.
  4. Test on 50 products; verify JSON parses and descriptions are adequate.
  5. Deploy.
CONFIRM: About to set max_tokens=300 and switch to JSON output on
  product-desc-gen. Monthly saving $1,350.00 (66.2%). Proceed? (yes/no)
```

## Worked example — already optimal

```text
TARGET: anthropic.claude-3-haiku-20240307-v1:0 (email-classifier)
VERDICT: OPTIMIZED
REASON: Email classification workload already on Haiku (cheapest capable
  model for classification), prompt caching enabled with 94% hit rate,
  max_tokens=200 set, interactive workload (batch not eligible), no
  Guardrails, no KB. All seven dimensions verified — no further cost
  optimization available.
RECOMMENDATION:
  Current: Haiku, 400 input (350 cached), 50 output, 300,000 invocations/month — no change
  Dimensions checked: model ✓ (Haiku appropriate)  caching ✓ (94% hit rate)
    batch ✓ (interactive, not eligible)  response_length ✓ (max_tokens=200 set)
    fine_tune ✓ (output already minimal)  guardrails ✓ (none)  throughput ✓ (spend below threshold)
  Confidence: HIGH — all dimensions verified; $48.75/month is minimal.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Re-evaluate if invocation pattern changes or at
    quarterly FinOps review.
```

## Worked example — NEED_MORE_INFO (metrics absent)

```text
TARGET: unknown-model (newly-deployed-chatbot)
VERDICT: NEED_MORE_INFO
REASON: InputTokenCount and OutputTokenCount metrics are absent for the
  requested 30-day window. The model may be newly deployed, dormant, or
  the IAM role may deny cloudwatch:GetMetricStatistics. Cannot make a
  cost optimization recommendation without baseline token metrics.
RECOMMENDATION:
  Current: unknown model, unknown token usage — pending data
  Proposed: pending data
  Confidence: LOW — no metrics to evaluate.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify without baseline)
MIGRATION_STEPS:
  1. Verify the model is being invoked:
     aws cloudwatch get-metric-statistics --namespace AWS/Bedrock
       --metric-name InvocationCount --dimensions Name=ModelId,Value=<id>
  2. Verify IAM permissions for CloudWatch:
     aws iam get-role-policy --role-name <role> --policy-name <policy>
  3. Wait 14-30 days for representative observation.
  4. Re-evaluate with InputTokenCount + OutputTokenCount data.
  Do NOT optimize based on assumed metrics.
```

## End-to-end optimisation walkthrough ($10,200/month workload)

This example walks through the complete workflow: analyse token
metrics, identify the model downgrade opportunity, evaluate caching,
calculate savings, and provide migration steps.

**Workload profile:**
- Model: `anthropic.claude-3-opus-20240229-v1:0`
- Workload: Customer support FAQ chatbot
- InputTokenCount: 500M/month (avg 2,500/invocation, 2,000 system prompt)
- OutputTokenCount: 36M/month (avg 180/invocation)
- InvocationCount: 200,000/month
- InvocationLatency: avg 3,200 ms, p95 5,800 ms
- Region: us-east-1, on-demand

**Step 1 — Analyse current cost:**
```
Current input:  500M / 1000 × $0.015 = $7,500/month
Current output: 36M / 1000 × $0.075 = $2,700/month
Current total: $10,200/month ($122,400/year)
```

**Step 2 — Route through model selection gate:**
- Task type: FAQ Q&A (classification/lookup) → Haiku tier
- Output < 200 tokens → confirms no complex generation
- System prompt 2,000 tokens repeated → caching candidate

**Step 3 — Evaluate caching:**
- System prompt: 2,000 tokens, static across all invocations
- Invocation rate: 200,000/month ≈ 0.077/sec (one every ~13 seconds)
- Cache TTL: 5 minutes (300 seconds)
- Between cache writes: ~23 invocations per TTL window
- Projected cache hit rate: ~95%+ (only first invocation per window misses)

**Step 4 — Calculate projected cost on Haiku + caching:**
```
Projected input (non-cached portion):
  500 tokens (user query) × 200,000 / 1000 × $0.00025 = $25.00
Projected input (cache write):
  2,000 tokens × ~12,000 cache writes / 1000 × $0.00031 = $7.44
Projected input (cache read):
  2,000 tokens × ~188,000 cache hits / 1000 × $0.000025 = $9.40
Projected output:
  36M / 1000 × $0.00125 = $45.00
Projected total: ~$86.84/month
```

**Step 5 — Savings summary:**
```
Monthly saving: $10,200 − $86.84 = $10,113.16 (99.1%)
Annual saving: $121,357.92
Latency improvement: p95 drops from 5,800 ms to ~800 ms (Haiku is faster for simple tasks)
```

**Step 6 — Emit the output block:** (see the first worked example above)

## Response length control math (moved from SKILL.md)

**Worked example:**
```
Without max_tokens:
  Average output: 800 tokens × $0.015/1k (Sonnet output) = $0.012/invocation
  1M invocations/month = $12,000/month on output

With max_tokens=200 + "Answer concisely in JSON":
  Average output: 150 tokens × $0.015/1k = $0.00225/invocation
  1M invocations/month = $2,250/month on output
  Saving: $9,750/month (81%)
```

## Output block template (moved from SKILL.md)

```text
TARGET: <model-id or workload-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <model>, <input tokens/invocation>, <output tokens/invocation>, <invocations/month>
  Proposed: <model>, <projected input tokens>, <projected output tokens>, <invocations/month>
  Dimensions changed: <model | caching | batch | response_length | fine_tune | guardrails | throughput>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>
    input tokens: <count> × $<rate>/1k = $<amount>
    output tokens: <count> × $<rate>/1k = $<amount>
    guardrails: $<amount>
    KB: $<amount>
  Projected monthly: $<amount>
  Monthly saving: $<amount>    ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>     ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <model/workload> in <region>.
  Proceed? (yes/no)"
```
