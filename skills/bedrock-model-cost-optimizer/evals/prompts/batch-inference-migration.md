# Eval prompt: batch-inference-migration

Optimise the following Bedrock workload for cost. Walk all optimization
dimensions (model selection, caching, batch, response length,
fine-tuning, guardrails, throughput) and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

Workload: batch-inference-migration (bulk document summarisation)
ModelId: anthropic.claude-3-haiku-20240307-v1:0
Region: us-east-1
Pricing: on-demand

Metrics (last 30 days):
  - InputTokenCount total: 750,000,000 (avg 1,500/invocation)
  - OutputTokenCount total: 250,000,000 (avg 500/invocation)
  - InvocationCount: 500,000
  - InvocationLatency avg: 1,800 ms, p95: 2,900 ms
  - ThrottledInvocationCount: 12,000 (2.4%)

Workload context: bulk summarisation of internal documents (PDF
transcripts, meeting notes). Results are consumed by a nightly search
indexing pipeline — no user is waiting for real-time responses. 500k
documents/month, batch of 1 per invocation.

Cost Explorer: $500/month on Bedrock.
