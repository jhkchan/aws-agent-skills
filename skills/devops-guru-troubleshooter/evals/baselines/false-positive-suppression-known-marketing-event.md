# Baseline (no-skill) — false-positive-suppression-known-marketing-event

> This is the response a model produces **without** the skill definition.
> It identifies the traffic spike but does not provide a durable
> suppression strategy (console dismiss only) and does not verify the
> benign nature of the anomaly (2XX scaling proportionally, no latency
> degradation). Generated for with-skill-vs-baseline comparison.

---

The DevOps Guru insight shows a traffic spike on your ALB. If this is
from a known marketing campaign, you can dismiss it:

1. Open the DevOps Guru console.
2. Find insight z-9012ijkl.
3. Click "Dismiss" to suppress the insight.

The traffic spike appears to be from the marketing campaign. The ALB
should handle it fine.
