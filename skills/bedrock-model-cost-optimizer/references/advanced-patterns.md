# Advanced Patterns (load on demand) — Bedrock Model Cost Optimizer

Edge-case catalogs, expert-knowledge deep dives, quick-start rules, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Quick start — five headline rules and the cost formula (moved from SKILL.md)

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

## Mindset — why model selection is the #1 lever (moved from SKILL.md)

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

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

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

## Model routing pattern (Haiku classifier) (moved from SKILL.md)

**Model routing pattern:** For mixed-complexity workloads, route via
a lightweight Haiku classifier:

```
User query → Haiku classifier →
  ├── "simple" → Haiku (handles query directly)
  └── "complex" → Sonnet or Opus (handles query)
```

This adds one Haiku invocation per query but moves 70-80% of traffic
to the cheapest tier. Net positive when simple-query rate > 50%.

## Recent AWS features (2024-2026) (moved from SKILL.md)

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
