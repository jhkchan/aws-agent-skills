# Error Handling — Aurora Cost Optimizer

Load-on-demand output-contract enforcement and data-gate failure templates moved verbatim from SKILL.md.

## FORBIDDEN output patterns

1. **NEVER preface the block with prose, greetings, or "Here is...".**
   The first line of the response MUST be `TARGET:`.
2. **NEVER emit `VERDICT: OPPORTUNITY_FOUND` with `Annual total: $0`.**
   If no dimension produces a savings line > $0, the verdict MUST be
   `ALREADY_OPTIMAL`.
3. **NEVER show savings math that does not balance.** Right-sizing +
   ACU + I/O + storage + Global DB + backtrack + RI subtotals MUST
   sum to the displayed annual total (×12 of monthly sum).
4. **NEVER recommend Aurora I/O-Optimized without computing the
   break-even I/O count.** Always cite `break-even = storage_GB × 0.4`
   million I/O/month and the actual measured I/O.
5. **NEVER recommend an RI without stating the term (1-yr/3-yr), the
   offering class (No Upfront/Partial/All), and the exact instance
   class.** A bare "buy an RI" recommendation is not actionable.
6. **NEVER recommend right-sizing the writer based on CPU alone.** The
   recommendation MUST cite Performance Insights DBLoad OR explicitly
   state "PI not enabled — recommendation based on CPU only, MEDIUM
   confidence."
7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision (e.g., $0.12/ACU-h × 730h =
   $87.60, not $88), round only the displayed result.

## Step 1 — NEED_MORE_INFO template (missing Cost Explorer access)


```text
TARGET: <cluster-identifier>
VERDICT: NEED_MORE_INFO
REASON: Cost Explorer access is required to quantify per-dimension
  savings. Without USAGE_TYPE granularity (Aurora:InstanceUsage,
  Aurora:StorageUsage, Aurora:IOUsage, Aurora:ServerlessUsage), the
  seven dimensions can be analysed qualitatively but the dollar
  savings cannot be computed.
RECOMMENDATION:
  1. Grant the auditor role `ce:GetCostAndUsage`.
  2. Or, paste the top 10 Aurora USAGE_TYPE line items from the
     last 30 days of CUR.
ESTIMATED_SAVINGS: $0 (cannot quantify without CUR data)
MIGRATION_STEPS:
  - IAM policy addition:
    {"Effect":"Allow",
     "Action":["ce:GetCostAndUsage","ce:GetDimensionValues"],
     "Resource":"*"}
```
