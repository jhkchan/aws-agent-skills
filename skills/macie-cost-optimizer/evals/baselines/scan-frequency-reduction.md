# Baseline (no-skill) response: scan-frequency-reduction

This file captures what a generic assistant produces WITHOUT the
macie-cost-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, per-GB frequency math, dollar
savings estimate, CONFIRM gate).

---

Your weekly Macie compliance scan is processing about 8 TB across 3
buckets every month. Since your compliance window is quarterly, you
could reduce the frequency to monthly instead of weekly.

Going from weekly (4 runs/month) to monthly (1 run/month) would cut
your assessment cost by about 75%. At your current $800/month spend,
that's roughly $600 in savings.

You can update the job schedule with:

```
aws macie2 update-classification-job --job-id job-weekly-compliance-scan --schedule-frequency --monthly
```

Just make sure your compliance officer has signed off on the monthly
cadence, which it sounds like they have.
