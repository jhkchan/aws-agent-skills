# Eval prompt: prompt-caching-opportunity

Optimise the following Bedrock workload for cost. Walk all optimization
dimensions (model selection, caching, batch, response length,
fine-tuning, guardrails, throughput) and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

Workload: prompt-caching-opportunity (legal document analyser)
ModelId: anthropic.claude-3-5-sonnet-20241022-v2:0
Region: us-east-1
Pricing: on-demand

Metrics (last 30 days):
  - InputTokenCount total: 180,000,000 (avg 3,000/invocation)
  - OutputTokenCount total: 30,000,000 (avg 500/invocation)
  - InvocationCount: 60,000
  - InvocationLatency avg: 2,100 ms, p95: 3,400 ms
  - ThrottledInvocationCount: 0

Workload context: legal document clause extraction. System prompt is
2,800 tokens of legal instructions + output format spec, repeated on
every invocation. User query (200 tokens) varies per invocation.
Invocation rate ~2/sec (steady, well within cache TTL). Prompt caching
is NOT currently enabled.

Cost Explorer: $990/month on Bedrock.
