# Eval prompt: opus-to-haiku-downgrade

Optimise the following Bedrock workload for cost. Walk all optimization
dimensions (model selection, caching, batch, response length,
fine-tuning, guardrails, throughput) and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

Workload: opus-to-haiku-downgrade (customer support chatbot)
ModelId: anthropic.claude-3-opus-20240229-v1:0
Region: us-east-1
Pricing: on-demand

Metrics (last 30 days):
  - InputTokenCount total: 500,000,000 (avg 2,500/invocation)
  - OutputTokenCount total: 36,000,000 (avg 180/invocation)
  - InvocationCount: 200,000
  - InvocationLatency avg: 3,200 ms, p95: 5,800 ms
  - ThrottledInvocationCount: 0

Workload context: FAQ Q&A. System prompt is 2,000 tokens of company
policy + FAQ, repeated on every invocation. Responses are short (avg
180 output tokens). No batch processing.

Cost Explorer: $10,200/month on Bedrock (Service=Bedrock).
