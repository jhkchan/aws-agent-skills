# Example usage: bedrock-model-cost-optimizer

A walkthrough showing the skill optimizing a customer support chatbot
running on Claude Opus, demonstrating the model downgrade to Haiku,
prompt caching enablement, the dollar savings math, and the staged
canary cutover.

## Input (user prompt)

> Review our Bedrock spend before the Q3 GenAI FinOps review. Our
> customer support chatbot is running on Opus and it's expensive.
> Help me optimize the cost.

```text
Workload: support-chatbot-prod (customer support FAQ Q&A)
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
180 output tokens). No batch processing. Interactive chatbot.

Cost Explorer: $10,200/month on Bedrock (Service=Bedrock).
```

## Skill output

```text
TARGET: anthropic.claude-3-opus-20240229-v1:0 (support-chatbot-prod)
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
CONFIRM: About to downgrade support-chatbot-prod from Opus to Haiku
  and enable prompt caching. Monthly saving $10,052.50 (98.6%). Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **Haiku is ~60x cheaper, not "somewhat cheaper."** A generic
   assistant says "Haiku would be cheaper." The skill cites the exact
   per-token cost differential ($0.015 → $0.00025 input; $0.075 →
   $0.00125 output) and computes the dollar savings at current volume.

2. **Prompt caching stacks on top of the model downgrade.** The skill
   stacks two savings: model downgrade (60x) + prompt caching (89% on
   the 2,000-token system prompt). A generic assistant captures only
   the model change.

3. **Output token economics drive the cost model.** The skill identifies
   that output tokens cost 5x more than input tokens and verifies that
   180 avg output tokens confirms the task is Haiku-appropriate (no
   complex generation). A generic assistant does not analyse the
   output-to-input token ratio.

4. **Canary test workflow.** The skill routes 10% traffic to Haiku for
   7 days before full cutover, with a Bedrock model evaluation job to
   objectively compare quality. A generic assistant goes straight to a
   modelId swap.

5. **All seven dimensions verified.** The skill explicitly checks batch
   eligibility (interactive → not eligible), fine-tuning viability
   (invocations too low), Guardrails (none configured), and provisioned
   throughput (spend below threshold). A generic assistant focuses only
   on the model swap.

6. **Cost arithmetic is shown explicitly.** The skill shows the formula
   (500M × $0.015/1k = $7,500) so the operator can verify. The savings
   math is internally consistent ($10,200 − $147.50 = $10,052.50).

## Slash-command invocation

```
/aws:optimize-bedrock-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimise our Bedrock spend for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: bedrock-model-cost-optimizer]` and
hands off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm token counts on the new model
aws cloudwatch get-metric-statistics --namespace AWS/Bedrock \
  --metric-name InputTokenCount \
  --dimensions Name=ModelId,Value=anthropic.claude-3-haiku-20240307-v1:0 \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 86400 --statistics Sum --output json

# Verify cache hit rate
aws cloudwatch get-metric-statistics --namespace AWS/Bedrock \
  --metric-name CacheReadInputTokenCount \
  --dimensions Name=ModelId,Value=anthropic.claude-3-haiku-20240307-v1:0 \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 86400 --statistics Sum --output json

# Confirm Cost Explorer spend dropped
aws ce get-cost-and-usage \
  --time-period Start=2026-08-04,End=2026-08-11 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"Service","Values":["Amazon Bedrock"]}}' \
  --metrics "UnblendedCost" --output json
```

If quality regresses, roll back by switching the modelId back to Opus
in the application configuration.

## Fleet-wide extension

For a fleet of N Bedrock workloads, run the skill in batch mode:

1. Pull all models with `aws bedrock list-foundation-models`.
2. Pull CloudWatch token metrics for each model over 30 days.
3. Classify each by task type (classification, reasoning, creative).
4. Sort by estimated monthly savings (largest first).
5. Slice into batches of 3 model changes.
6. For each batch: emit per-workload MIGRATION_STEPS, then a single
   CONFIRM for the batch.
7. Verify each batch before proceeding to the next.
8. After model downgrades, evaluate caching eligibility for all
   remaining workloads with static system prompts.
