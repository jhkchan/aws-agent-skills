# Error Handling (load on demand) — Bedrock Model Cost Optimizer

Data-quality failure modes and short-circuit tables moved verbatim from SKILL.md. Loaded on demand.

---

## Data-quality short-circuits (moved from SKILL.md)

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
