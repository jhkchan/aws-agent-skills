# Eval prompt: already-optimized-workload

Optimise the following Bedrock workload for cost. Walk all optimization
dimensions (model selection, caching, batch, response length,
fine-tuning, guardrails, throughput) and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

Workload: already-optimized-workload (email classifier)
ModelId: anthropic.claude-3-haiku-20240307-v1:0
Region: us-east-1
Pricing: on-demand

Metrics (last 30 days):
  - InputTokenCount total: 120,000,000 (avg 400/invocation, of which
    350 are cached system prompt)
  - OutputTokenCount total: 15,000,000 (avg 50/invocation)
  - InvocationCount: 300,000
  - InvocationLatency avg: 450 ms, p95: 800 ms
  - ThrottledInvocationCount: 0

Workload context: email classification (spam/not-spam/priority).
System prompt (350 tokens, classification instructions) is cached via
prompt caching (cache hit rate 94%). max_tokens=200 set. Interactive
workload (batch not eligible). No Guardrails. No KB.

Cost Explorer: $48.75/month on Bedrock.
