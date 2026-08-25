# Worked examples - S3 Intelligent-Tiering Optimizer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — small objects rejected by monitoring-fee gate

This example demonstrates the **negative-savings rule**: when the
monitoring fee exceeds the transition saving, the verdict is
`ALREADY_OPTIMAL`, never `OPPORTUNITY_FOUND` with negative savings.

```text
BUCKET: app-config-state
VERDICT: ALREADY_OPTIMAL
REASON: Bucket contains 8.2M objects averaging 4.2 KB each (Step 2
  monitoring-fee gate FAILS). The monitoring fee ($20.50/month) alone
  exceeds the entire projected transition saving ($0 — objects below
  the Infrequent tier's 128 KB minimum billable size cannot save).
  Intelligent-Tiering is REJECTED. Standard is already the cheapest
  tier for this object-size profile.
RECOMMENDATION: No changes required. Optionally enable small-object fee
  aggregation for cost-allocation visibility (does NOT change the
  monitoring-fee math).
SAVINGS:
  CURRENT_MONTHLY: $10.09
    - Storage: 32.0 GiB × $0.023 = $0.74
    - GETs: 8.2M × 3/month × $0.00038/1K = $9.35
    - PUTs: negligible (write-once workload)
  PROJECTED_MONTHLY (Intelligent-Tiering, best case):
    - Monitoring fee: 8,200,000 / 1,000 × $0.0025 = $20.50
    - Storage: 32.0 GiB × $0.023 = $0.74 (no saving — all objects < 128 KB)
    - GETs: 8.2M × 3/month × $0.00038/1K = $9.35
    - Total projected: $30.59
  MONTHLY_SAVING: -$20.50  (NEGATIVE — monitoring fee alone exceeds saving)
  ANNUAL_SAVING: -$246.00
  CAVEATS: The proposed plan INCREASES cost by $20.50/month. The verdict
    is ALREADY_OPTIMAL because Standard is already the cheapest applicable
    tier for this object-size profile. Do NOT enable Intelligent-Tiering.
IMPLEMENTATION: None required. Re-evaluate if average object size grows
  above 128 KB.
```

### Worked example — already optimal Intelligent-Tiering setup

```text
BUCKET: data-lake-curated
VERDICT: ALREADY_OPTIMAL
REASON: Bucket already has an Intelligent-Tiering configuration with
  Archive Access at 90 days and Deep Archive Access at 180 days, scoped
  to the correct prefix. Storage Lens shows the tier distribution matches
  the access pattern (Frequent 22%, Infrequent 45%, Archive 23%, Deep
  Archive 10%). Monitoring fee ($150/month) is < 7% of the net saving
  ($2,100/month).
RECOMMENDATION: No changes required.
SAVINGS:
  CURRENT_MONTHLY: $2,890.00  (current Intelligent-Tiering blended)
  PROJECTED_MONTHLY: $2,890.00  (no change)
  MONTHLY_SAVING: $0.00
  ANNUAL_SAVING: $0.00
  CAVEATS: Monitoring fee: $150.00/month (60M objects). Tier distribution
    is healthy — no tuning required.
IMPLEMENTATION: None required. Posture is correct for the workload.
```

