# Eval prompt: response-length-control

Optimise the following Bedrock workload for cost. Walk all optimization
dimensions (model selection, caching, batch, response length,
fine-tuning, guardrails, throughput) and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

Workload: response-length-control (product description generator)
ModelId: anthropic.claude-3-5-sonnet-20241022-v2:0
Region: us-east-1
Pricing: on-demand

Metrics (last 30 days):
  - InputTokenCount total: 80,000,000 (avg 800/invocation)
  - OutputTokenCount total: 120,000,000 (avg 1,200/invocation)
  - InvocationCount: 100,000
  - InvocationLatency avg: 4,500 ms, p95: 7,200 ms
  - ThrottledInvocationCount: 0

Workload context: e-commerce product description generator. Input is
product specs (800 tokens). Output averages 1,200 tokens — verbose
prose where structured 300-token JSON would suffice. max_tokens is not
set (defaults to model max). No stop sequences.

Cost Explorer: $2,040/month on Bedrock ($240 input + $1,800 output).
