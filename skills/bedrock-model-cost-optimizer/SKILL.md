---
name: bedrock-model-cost-optimizer
description: 'Optimises Amazon Bedrock inference cost across seven dimensions: model selection (Claude Haiku is ~60x cheaper
  per token than Opus; Nova Micro cheaper still; route simple queries to cheapest capable model), token usage analysis (output
  tokens cost 3-5x more than input), prompt caching (cache repeated system prompts to reduce input cost by up to 90%; TTL
  5 min default, 1 hr max), batch inference (50% discount vs on-demand for non-latency-sensitive workloads), response length
  control (max_tokens, stop sequences, structured output), fine-tuning vs few-shot trade-off (fine-tune once then serve on
  cheaper base vs per-call in-context examples), and Guardrails / Knowledge Base overhead (Guardrails charges per processed
  token; KB adds vector store cost). Reads CloudWatch Bedrock metrics (InputTokenCount, OutputTokenCount, InvocationCount)
  and Cost Explorer. Emits OPTIMIZED or FURTHER_OPTIMIZATION_AVAILABLE. Use when reviewing Bedrock spend, planning model downgrades,
  evaluating prompt caching, or running a GenAI ...'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works
  from pasted CloudWatch Bedrock metrics and Cost Explorer data. Live-account optimization uses aws bedrock list-foundation-models,
  aws bedrock get-foundation-model, aws cloudwatch get-metric-statistics (AWS/Bedrock namespace), aws ce get-cost-and-usage
  (Service=Bedrock), aws bedrock create-prompt, aws bedrock create-guardrail, aws bedrock create-model-invocation-job (batch),
  and aws bedrock get-use-case-with-responses (KB; AWS CLI v2, SSO or key-based credentials). Pricing references us-east-1
  published rates as of 2026.
keywords:
- Bedrock
- model selection
- cost optimization
- prompt caching
- batch inference
- token usage
- Claude Haiku
- Claude Sonnet
- Claude Opus
- Nova Micro
- Nova Lite
- Nova Pro
- input tokens
- output tokens
- max_tokens
- stop sequences
- fine-tuning
- few-shot
- Guardrails
- Knowledge Base
- provisioned throughput
- on-demand
- model routing
- embedding
- Titan embeddings
- Cohere embeddings
- CloudWatch Bedrock metrics
- GenAI FinOps
tags:
- bedrock
- ai-ml
- cost-optimization
- genai-finops
- prompt-caching
- batch-inference
- model-selection
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: AI/ML
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising Bedrock inference spend, triaging model selection (downgrading Opus to Haiku for simple queries),
    evaluating prompt caching eligibility for repeated system prompts, planning batch inference for non-real-time workloads,
    controlling response length via max_tokens and stop sequences, deciding fine-tune vs few-shot for a high-volume use case,
    estimating Guardrails or Knowledge Base cost overhead, or running a GenAI FinOps review on Bedrock spend.
  when_not_to_use: EC2 instance rightsizing for self-hosted models (use ec2-rightsizing-optimizer), Lambda function cost (use
    lambda-cost-optimizer), SageMaker endpoint cost (use sagemaker-cost-optimizer if available), or Bedrock model troubleshooting
    (invocation errors, throttling, content policy blocks — use the Bedrock troubleshooter). This skill focuses on cost-driven
    optimization decisions, not functional debugging of broken invocations.
  activation_triggers:
  - optimise Bedrock cost
  - Bedrock model selection
  - Bedrock prompt caching
  - Bedrock batch inference
  - Bedrock token usage
  - Bedrock max_tokens optimization
  - Bedrock fine-tuning cost
  - Bedrock Guardrails overhead
  - Bedrock Knowledge Base cost
  - Bedrock provisioned throughput
  - Bedrock model routing
  - Bedrock embedding model
  - Bedrock CloudWatch metrics
  - Bedrock GenAI FinOps
  - Claude Haiku vs Sonnet vs Opus cost
  - Nova model pricing
  - reduce Bedrock bill
  - Bedrock monthly savings estimate
  invocation_schema: 'Input: either (a) a model identifier + live-account context with CloudWatch Bedrock metrics, (b) a Cost
    Explorer Bedrock spend breakdown, OR (c) a prompt/workflow description with token usage data (InputTokenCount, OutputTokenCount,
    InvocationCount over 14-30 days). Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS
    block per model or workflow, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "ModelId: anthropic.claude-3-opus-20240229-v1:0\nRegion: us-east-1\nPricing: on-demand\nMetrics (last\
    \ 30 days):\n  - InputTokenCount total: 500,000,000 (avg 2,500/invocation)\n  - OutputTokenCount total: 100,000,000 (avg\
    \ 500/invocation)\n  - InvocationCount: 200,000\n  - InvocationLatency avg: 3,200 ms, p95: 5,800 ms\nWorkload: customer\
    \ support chatbot. System prompt is 2,000 tokens\nof company policy + FAQ, repeated on every invocation.\nCost Explorer:\
    \ $4,800/month on Bedrock.\nEmit the standard optimization block."
---

# Bedrock Model Cost Optimizer

## What this skill does

Translates a Bedrock model or generative-AI workload's inference posture
into a concrete cost-optimization recommendation with a dollar-denominated
savings estimate. The verdict is the highest-leverage action across seven
dimensions — model selection, prompt caching, batch inference, response
length control, fine-tuning vs few-shot, Guardrails and KB overhead, and
provisioned throughput — applied in priority order. Always pairs the
recommendation with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Five headline rules and the cost formula | First read |
| Mindset | Why model selection is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a workload |
| Pre-flight data gate | CloudWatch Bedrock metrics, Cost Explorer | Before any recommendation |
| Step 0 non-obvious behaviours | Output token pricing, cache TTL, batch latency | Edge cases |
| Step 1 Model selection | Haiku vs Sonnet vs Opus, Nova family, routing | The headline savings dimension |
| Step 2 Prompt caching | Cache system prompts, reduce input cost 90% | Repeated context workloads |
| Step 3 Batch inference | 50% discount for non-real-time workloads | Document processing, dataset gen |
| Step 4 Response length control | max_tokens, stop sequences, structured output | Verbose model outputs |
| Step 5 Fine-tuning vs few-shot | One-time cost vs per-call overhead | High-volume specialised tasks |
| Step 6 Guardrails / KB overhead | Per-token charges, vector store cost | Compliance / RAG workloads |
| Step 7 Provisioned throughput | On-demand vs committed discount | Steady-state high volume |
| Step 8 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, canary test, rollback | Before any apply CLI |

## Quick start

- **Model selection is the #1 lever.** Claude Haiku is ~60x cheaper
  per token than Opus and handles the majority of production workloads
  (classification, extraction, simple Q&A, summarisation). Route only
  complex reasoning tasks to Sonnet or Opus. A blanket Opus policy is
  the single most expensive Bedrock mistake.
- **Cost formula (memorise this):**
  `monthly_cost = (input_tokens × input_price_per_1k) + (output_tokens × output_price_per_1k)`
  Where input and output prices differ by model (see pricing reference).
- **Prompt caching saves up to 90% on repeated context.** If a system
  prompt or knowledge context is reused across invocations, cache it.
  Cache hits cost ~10% of the normal input token rate. TTL is 5 minutes
  default, 1 hour maximum.
- **Batch inference gives 50% discount.** For non-latency-sensitive
  workloads (document processing, dataset generation, bulk classification),
  use the Bedrock Batch API instead of real-time InvokeModel.
- **Output tokens cost 3-5x more than input tokens.** Across Claude and
  Nova families, output token pricing is 3-5x the input rate. Reducing
  output length via max_tokens, stop sequences, or structured output
  has a disproportionate cost impact.

## Mindset

Bedrock cost optimization is a model-and-context decision, not a pure
infrastructure exercise. The goal is the cheapest model + context strategy
that preserves output quality — not the most powerful model applied
uniformly to every call.

Four principles guide every recommendation:

- **The model hierarchy is a cost ladder.** Opus > Sonnet > Haiku in
  both capability and price. Most production traffic should land on
  Haiku or Nova Micro/Lite; reserve Sonnet/Opus for the minority of
  calls that genuinely require deep reasoning. Model routing (routing
  simple queries to Haiku, complex ones to Sonnet) captures both tiers.
- **Prompt caching amortises repeated context.** System prompts,
  knowledge base context, and few-shot examples are re-sent on every
  invocation. Caching turns a $5,000/month input token bill into
  $500/month for the cached portion.
- **Batch shifts the pricing model.** Batch inference is 50% cheaper
  but adds latency (minutes to hours). It is ideal for offline
  workloads and eliminates throttling concerns.
- **Output is more expensive than input.** A model that produces
  verbose 1,000-token responses costs 3-5x more than one that produces
  200-token responses for the same input. Response length control is
  a pure cost lever with no quality trade-off when structured output
  is acceptable.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Model is Opus or Sonnet AND workload is classification / extraction / simple Q&A / summarisation | **FURTHER_OPTIMIZATION_AVAILABLE** (model) | Step 1 — downgrade to Haiku or Nova Micro/Lite |
| Model is Opus AND workload requires reasoning but not frontier-level | **FURTHER_OPTIMIZATION_AVAILABLE** (model) | Step 1 — downgrade to Sonnet (5-7x cheaper than Opus) |
| System prompt or KB context > 1,000 tokens AND repeated across invocations AND prompt caching not enabled | **FURTHER_OPTIMIZATION_AVAILABLE** (caching) | Step 2 — enable prompt caching |
| Workload is non-real-time (document processing, dataset generation, bulk classification) AND using InvokeModel | **FURTHER_OPTIMIZATION_AVAILABLE** (batch) | Step 3 — migrate to Bedrock Batch API |
| Average output tokens > 1,000 AND max_tokens not set or set too high | **FURTHER_OPTIMIZATION_AVAILABLE** (response length) | Step 4 — set max_tokens, add stop sequences |
| Few-shot examples > 500 tokens per invocation AND invocation count > 100k/month | **FURTHER_OPTIMIZATION_AVAILABLE** (fine-tune) | Step 5 — fine-tune on a cheaper base model |
| Guardrails enabled AND processing > 1B tokens/month | **FURTHER_OPTIMIZATION_AVAILABLE** (guardrail scope) | Step 6 — narrow guardrail to output-only or reduce scope |
| On-demand spend > $10,000/month AND traffic is steady (CV < 0.3) | **FURTHER_OPTIMIZATION_AVAILABLE** (throughput) | Step 7 — evaluate provisioned throughput |
| All dimensions verified AND model is Haiku/Nova AND caching enabled where applicable AND no batch-eligible workload | **OPTIMIZED** | None — continue monitoring |
| InputTokenCount / OutputTokenCount metrics absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI in
`references/bedrock-pricing-and-token-metrics.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Model list and access: `aws bedrock list-foundation-models`
2. InputTokenCount + OutputTokenCount (14-30 day window): `aws cloudwatch get-metric-statistics --namespace AWS/Bedrock`
3. InvocationCount + InvocationLatency: same namespace
4. Cost Explorer spend: `aws ce get-cost-and-usage --filter Service=Bedrock`
5. Prompt caching config: `aws bedrock get-prompt` or inspect application code
6. Guardrails: `aws bedrock list-guardrails`, `aws bedrock get-guardrail`
7. Batch jobs: `aws bedrock list-model-invocation-jobs`

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `InputTokenCount` metric absent (no invocations in window) | **NEED_MORE_INFO**. Verify model is being invoked; skip until traffic exists. |
| `InvocationCount` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "dormant model — no spend." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| Cost Explorer shows $0 but CloudWatch shows invocations | Free tier or billing delay. Use token-based cost estimate instead. |
| `ThrottledInvocationCount` > 1% of InvocationCount | Throughput-limited; consider provisioned throughput (Step 7) or batch (Step 3). |
| Model not in `list-foundation-models` (access denied) | Model not enabled in region. `aws bedrock get-foundation-model --model-identifier <id>` to check. |

When CloudWatch and Cost Explorer disagree, Cost Explorer is the source
of truth for actual spend; CloudWatch token counts drive optimization modeling.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious:
- **Output tokens cost 3-5x more than input tokens.** Across Claude
  models, output is ~5x the input rate; across Nova, ~3x. A model that
  halves output length saves more than one that halves input length.
- **Prompt caching has a write premium.** The first invocation populates
  the cache at ~1.25x the normal input rate; cache hits serve at ~0.1x.
  Net positive only if the cache is hit > 2x within the TTL window.
- **Cache TTL is 5 minutes default, 1 hour maximum.** Low-traffic
  workloads may not hit the cache before it expires. Evaluate cache hit
  rate before assuming savings.
- **Batch API has a completion SLA of hours, not seconds.** Do not
  migrate real-time or interactive workloads to batch.
- **Fine-tuning has a one-time training cost.** Amortise across expected
  invocation volume to determine break-even vs few-shot.
- **Guardrails charge per processed token.** Applying guardrails to both
  input and output doubles the overhead. Narrow to output-only where
  possible.
- **Knowledge Base retrieval adds vector store cost.** Bedrock KB backed
  by OpenSearch Serverless incurs OCU charges regardless of query volume.
  For low-volume RAG, this can exceed the model invocation cost.
- **Provisioned throughput requires a time commitment.** Underutilisation
  is wasted spend; overestimating traffic is costly.
- **Embedding model selection matters for RAG cost.** Titan Embed Text
  v2 is cheaper per token than Cohere Embed.
- **Model routing adds latency.** A Haiku classifier routing to Sonnet
  adds one extra invocation. Net positive only when most queries stay
  on Haiku.

### Step 1: Model selection (the #1 lever)

Model selection is the primary cost lever because the price delta
between model tiers is massive — Haiku is ~60x cheaper than Opus per
token. Downgrading a model that is over-provisioned for the task is the
single highest-impact optimization.

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

**Task-to-model routing matrix:**

| Task complexity | Example tasks | Recommended model | Cost vs Opus |
|---|---|---|---|
| Low | Classification, entity extraction, simple Q&A, formatting, sentiment | Haiku or Nova Micro/Lite | ~60x cheaper |
| Medium | Summarisation, code review, multi-step reasoning (2-3 steps), translation | Sonnet or Nova Pro | ~5-7x cheaper |
| High | Complex code generation, deep analysis, creative writing, multi-step reasoning (5+ steps) | Opus | Baseline |

**Decision gate for model downgrade:**

| Current model | Workload signal | Target model | Verdict |
|---|---|---|---|
| Opus | Output < 200 tokens avg, task is extraction/classification | Haiku | **FURTHER_OPTIMIZATION_AVAILABLE** |
| Opus | Task requires reasoning but not frontier-level | Sonnet | **FURTHER_OPTIMIZATION_AVAILABLE** |
| Sonnet | Output < 200 tokens avg, task is simple Q&A | Haiku | **FURTHER_OPTIMIZATION_AVAILABLE** |
| Haiku | Already on cheapest capable model | — | No model finding |
| Any | Quality regression after downgrade (user reports, eval scores drop > 5%) | Revert | Do NOT downgrade |

**Model routing pattern:** For mixed-complexity workloads, route via
a lightweight Haiku classifier:

```
User query → Haiku classifier →
  ├── "simple" → Haiku (handles query directly)
  └── "complex" → Sonnet or Opus (handles query)
```

This adds one Haiku invocation per query but moves 70-80% of traffic
to the cheapest tier. Net positive when simple-query rate > 50%.

### Step 2: Prompt caching (reduce input cost by 90%)

Prompt caching caches a prefix of the prompt (system prompt, knowledge
context, few-shot examples) so that repeated invocations with the same
prefix pay only ~10% of the normal input token rate for the cached
portion.

**Eligibility checklist:**

| Condition | Cache eligible? |
|---|---|
| System prompt > 1,000 tokens AND repeated across invocations | YES |
| Knowledge base context injected as static prefix | YES |
| Few-shot examples embedded in prompt | YES |
| Dynamic user query varies per invocation | Prefix still cacheable; query goes after cache boundary |
| System prompt changes per user or per session | NO (cache misses) |
| Invocation rate < 1 per 5 minutes | NO (cache expires before reuse) |

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

### Step 3: Batch inference (50% discount)

The Bedrock Batch API (`CreateModelInvocationJob`) processes large
datasets asynchronously at a 50% discount versus on-demand real-time
invocation.

**Eligibility:**

| Workload characteristic | Batch eligible? |
|---|---|
| Non-real-time (no user waiting for response) | YES |
| Document processing (summarise 10,000 PDFs) | YES |
| Dataset generation (create training data) | YES |
| Bulk classification / labelling | YES |
| Model evaluation runs | YES |
| Interactive chatbot | NO |
| Real-time API endpoint | NO |
| Streaming responses required | NO |

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

**Batch completion time:** Typically minutes to hours depending on
dataset size. The job runs asynchronously and writes results to S3.

### Step 4: Response length control

Output tokens cost 3-5x more than input tokens. Reducing output length
is a direct cost saving with no infrastructure change.

**Levers:**

| Lever | How | Typical saving |
|---|---|---|
| `max_tokens` | Set to the minimum acceptable response length | 20-60% on output cost |
| Stop sequences | Define stop words that truncate generation early | 10-30% on output cost |
| Structured output (tool use) | Force JSON/array format instead of prose | 30-70% on output cost |
| Prompt engineering ("Answer in 2 sentences") | Instruct model to be concise | 20-50% on output cost |

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

### Step 5: Fine-tuning vs few-shot

Few-shot examples (embedding 3-10 examples in the prompt) improve
output quality but add input token cost on every invocation. Fine-
tuning absorbs those examples into the model weights, allowing a
cheaper base model to achieve the same quality.

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

**Decision gate:**

| Condition | Recommendation |
|---|---|
| Few-shot tokens > 500/invocation AND invocations > 100k/month | Fine-tune (break-even < 3 months typically) |
| Few-shot tokens < 200/invocation OR invocations < 10k/month | Keep few-shot (fine-tune cost won't amortise) |
| Quality requirement is high AND base Haiku can't match Opus quality | Fine-tune Haiku on Opus outputs (distillation) |
| Few-shot examples change frequently | Keep few-shot (fine-tuning is too rigid) |

### Step 6: Guardrails and Knowledge Base overhead

**Guardrails cost model:**
```
Per invocation: guardrail processes input and/or output tokens.
Guardrail rate (us-east-1, 2026): ~$0.001/1k tokens processed

If applied to BOTH input and output:
  overhead = (input_tokens + output_tokens) × $0.001/1k

If applied to OUTPUT ONLY:
  overhead = output_tokens × $0.001/1k (50% reduction)
```

**Recommendation:** Apply guardrails to output only unless input
filtering is a compliance requirement. Output-only halves the overhead.

**Knowledge Base cost model:**
```
Per query: embedding_cost + vector_store_query_cost + model_invocation_cost

OpenSearch Serverless OCU: ~$400/month minimum (0.5 ingestion + 0.5 search)
  < 10k queries/month: OCU dominates → consider Pinecone or Neptune Analytics
  > 100k queries/month: model invocation dominates → OCU amortised
```

### Step 7: Provisioned throughput vs on-demand

Provisioned throughput purchases guaranteed model capacity at a
discounted rate for a time commitment. Suitable for steady-state,
high-volume workloads.

**Decision tree:**
```
Is monthly on-demand spend > $10,000?
├── NO → Stay on-demand. Provisioned commitment is not worth the complexity.
└── YES → Is traffic steady (coefficient of variation < 0.3)?
    ├── NO → Stay on-demand. Provisioned underutilisation wastes spend.
    └── YES → Is the model available for provisioned throughput?
        ├── NO → Stay on-demand.
        └── YES → Evaluate provisioned throughput quote vs on-demand cost.
```

**Provisioned throughput units:** Model-specific. One model unit
provides a fixed number of tokens per minute. Contact AWS for pricing
or check `aws bedrock list-foundation-models` for supported models.

### Step 8: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (monthly_input_tokens / 1000 × model_input_rate_per_1k)
  + (monthly_output_tokens / 1000 × model_output_rate_per_1k)
  + guardrail_overhead
  + kb_overhead

projected_monthly_cost =
  (projected_input_tokens / 1000 × new_model_input_rate_per_1k)
  + (projected_output_tokens / 1000 × new_model_output_rate_per_1k)
  + new_guardrail_overhead
  + new_kb_overhead

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: monthly token counts (input and output
separately), current and projected model, pricing region, caching
status, batch status, guardrail scope.

### Step 9: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND model is Haiku/Nova AND caching enabled where
  applicable AND no batch-eligible workload → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (InputTokenCount absent, window < 14 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO` gate.

## Output format

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

Full worked examples (model downgrade, prompt caching, batch migration,
already-optimal, NEED_MORE_INFO, and end-to-end walkthrough) are in
`references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.
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
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00`.** If every dimension nets zero cost delta,
   the verdict MUST be `OPTIMIZED`.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend a model downgrade without citing the task type and
   output token evidence.** The REASON MUST name the workload pattern
   that makes the downgrade safe.

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER present a quality regression as a cost saving.** If the
   downgrade risks quality loss, surface the risk in REASON and set
   Confidence to MEDIUM or LOW.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

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
  Proposed: Haiku, 2,500 input tokens/invocation (500 cached), 180 output tokens/invocation, 200,000 invocations/month
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
    ($10,200.00 − $147.50 = $10,052.50 ✓)
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

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | All dimensions pass (model is Haiku/Nova, caching enabled where applicable, no batch-eligible workload, response length controlled, guardrails scoped). Also emitted when a change was applied and verified this session. |
| `NEED_MORE_INFO` | Data gate failed: InputTokenCount/OutputTokenCount absent, window < 14 days, or model identifier unknown. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend a model downgrade without verifying the task type.**
   Opus/Sonnet are required for complex reasoning, code generation, and
   creative tasks. Always cite the task pattern that makes a downgrade safe.

2. **NEVER recommend prompt caching for low-traffic workloads.** If the
   cache expires before reuse, the write premium (1.25x) makes caching
   MORE expensive. Verify invocation rate > 1 per 5 minutes.

3. **NEVER recommend batch inference for interactive workloads.** Batch
   SLA is minutes to hours. Migrating a chatbot to batch breaks UX.

4. **NEVER recommend fine-tuning without computing break-even.** If
   invocation volume is low, the training cost never amortises.

5. **NEVER enable provisioned throughput without verifying traffic
   consistency.** Underutilisation is wasted spend. Only for steady-state,
   high-volume workloads (> $10,000/month on-demand).

Extended anti-patterns and error-handling tables in `references/bedrock-pricing-and-token-metrics.md`.
## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Canary test model downgrades.** Route 10% traffic to the new model
  for 7 days before full cutover.
- **Prompt caching is application-layer.** Changes to the invoke body
  require a code deploy, not an AWS CLI call. Coordinate with the app team.
- **Batch jobs write to S3.** Ensure the output bucket exists and the
  IAM role has write permissions before creating the job.
- **Fine-tuning requires training data.** Prepare 1,000-10,000 examples
  in JSONL. Training takes hours; monitor via
  `aws bedrock get-model-customization-job`.
- **Guardrail changes affect all invocations.** Test in staging first.
- **Provisioned throughput is a commitment.** Cost is incurred regardless
  of usage once purchased.
- **Embedding model changes require re-indexing.** Switching from Titan
  to Cohere changes vector dimensions; the entire KB must be re-indexed.
- **Bulk-operation limit:** Process at most 3 model changes per batch.
  Sort by estimated savings; abort if any model shows quality regression.

## Recent AWS features (2024-2026)

- **Bedrock Prompt Caching (2024-2025):** Caches prompt prefixes to
  reduce input token cost by up to 90%. Configured via `cache_control`
  in the invoke body. TTL 5 minutes default, 1 hour maximum.
- **Bedrock Batch API (2024):** `CreateModelInvocationJob` processes
  large datasets at 50% discount. Input/output via S3. Async completion.
- **Bedrock Guardrails (2024-2025):** Content filtering, denied topics,
  PII redaction. Charges per processed token. Input-only, output-only,
  or both.
- **Bedrock Knowledge Bases (2024-2025):** Managed RAG with OpenSearch
  Serverless, Pinecone, or Neptune Analytics vector stores.
- **Nova Model Family (2024-2025):** Amazon Nova Micro, Lite, Pro,
  Premier. Micro/Lite competitive with Haiku on price for simpler tasks.
- **Bedrock Model Evaluation (2024-2025):** `CreateEvaluationJob` for
  comparing model outputs on custom datasets. Validates downgrades.
- **Provisioned Throughput (2024-2025):** Committed-use discount for
  high-volume models. Hourly to monthly terms.
- **Titan Embed Text v2 (2024-2025):** Cheaper embedding model for RAG
  ingestion. Lower per-token rate than Cohere Embed.

## References

- `references/bedrock-pricing-and-token-metrics.md` — pricing tables by
  model family, token-to-cost formulas, CloudWatch Bedrock metric reference,
  prompt caching CLI, batch API reference, Guardrails pricing, KB vector
  store cost comparison, error-handling tables, fine-tuning decision tree,
  regional pricing multipliers.
- `references/worked-examples.md` — full worked examples (Opus-to-Haiku
  downgrade with caching, prompt caching enable, batch migration, response
  length control, already-optimal, NEED_MORE_INFO, end-to-end walkthrough).

## Domain

AWS CloudOps / Bedrock GenAI Cost Optimization & FinOps.

## AWS documentation

- **Bedrock User Guide** — https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html
- **Bedrock pricing** — https://aws.amazon.com/bedrock/pricing/
- **Bedrock prompt caching** — https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html
- **Bedrock batch inference** — https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html
- **Bedrock Guardrails** — https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html
- **Bedrock Knowledge Bases** — https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html
- **Bedrock CloudWatch metrics** — https://docs.aws.amazon.com/bedrock/latest/userguide/model-monitor-metrics.html
- **Bedrock provisioned throughput** — https://docs.aws.amazon.com/bedrock/latest/userguide/provisioned-throughput.html
- **AWS CLI Bedrock reference** — https://docs.aws.amazon.com/cli/latest/reference/bedrock/
- **Well-Architected Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
