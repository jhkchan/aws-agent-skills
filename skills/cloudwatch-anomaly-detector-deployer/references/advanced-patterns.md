# Advanced Patterns — CloudWatch Anomaly Detection Deployer

Deep-dive explanatory content moved out of the SKILL.md body for progressive disclosure: the two-week baseline requirement, metric compatibility edge cases, custom vs built-in metrics, and recent feature notes. Loaded on demand by the skill.

---

## Expert heuristic: the two-week baseline requirement

A baseline model says "create the detector and attach an alarm." The
correct heuristic recognizes that the ML model needs historical data to
learn the expected pattern, and without it, the band does not exist.

```text
Metric data timeline:
  Past ──────────────────────────────────── Present ──── Future
  │←──── historical data (>= 15 points) ────→│
  │                                          │
  │  Detector created here ─────────────────→│  LEARNING → TRAINED
  │                                          │
  │  Band available here ───────────────────→│  Alarm can fire
  │                                          │

If < 15 historical data points exist:
  Detector stays in LEARNING indefinitely
  Band never produced
  Alarm never fires (INSUFFICIENT_DATA)
```

**Key implication:** always verify the metric has at least 2 weeks of
historical data at the target period (5 min, 1 min, etc.) before
creating the detector. If the metric is new, wait 2 weeks before
deploying anomaly detection, or use a shorter-period metric that
accumulates 15 points faster.

---

## Step 2 — Metric compatibility check

**This is the most commonly skipped step and the #1 cause of "my
anomaly detector doesn't work" tickets.**

Not all CloudWatch metrics support anomaly detection. The model needs
metrics that produce regular, frequent data points with enough history.
The following metric characteristics indicate POOR compatibility:

| Metric characteristic | Why it fails | Recommendation |
|---|---|---|
| Sparse data (mostly zero, occasional spikes) | Model cannot learn a baseline from mostly-zero data | Use static threshold > 0 |
| Irregular intervals (data only when events occur) | No pattern to learn | Use static threshold or Logs Insights |
| Less than 15 data points at target period | Insufficient training data | Wait for more data; use shorter period |
| Constant value (no variability) | Model trains but band is trivially narrow; every change is anomalous | Use static threshold for delta detection |
| Counter metrics (monotonically increasing) | Model learns the rate of increase, not the absolute value | Use a rate/derivative metric instead |

**Compatible metrics (good candidates):**
- `AWS/EC2 CPUUtilization` — regular, frequent, diurnal patterns
- `AWS/ApplicationELB RequestCount` — traffic patterns
- `AWS/RDS DatabaseConnections` — usage patterns
- Custom metrics that report regularly (e.g., request latency, queue
  depth, active sessions)
- `AWS/NetworkELB ProcessedBytes` — network throughput patterns

**Verify metric compatibility:**

```bash
# Check if the metric has sufficient data points
aws cloudwatch get-metric-statistics \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --statistics Average \
  --period 300 \
  --start-time $(date -u -v-15d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --query 'Datapoints | length(@)' --output text
# Expected: >= 15 (ideally thousands for 2 weeks at 5-min period)
```

If the result is less than 15, the metric does not have enough data for
a reliable baseline. Output `VERDICT: PREREQUISITES_MISSING`.

---

## Step 11 — Custom metrics vs built-in

Anomaly detection works on BOTH built-in AWS metrics and custom metrics.
The configuration is identical; only the namespace and metric name
differ. Built-in AWS metrics (`AWS/EC2`, `AWS/RDS`, `AWS/ApplicationELB`)
are well-tested. Custom metrics work if they report regularly at 1-min
or 5-min resolution. High-resolution custom metrics (1-second) also
work but accumulate training data faster. Container Insights and Lambda
Insights metrics are supported — check for sparse data on low-traffic
functions.

---

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **Cross-account observability GA (2023-2024):** Anomaly detectors
  and alarms in a central monitoring account evaluating metrics from
  multiple member accounts.
- **High-resolution metric support (2023-2024):** 1-second resolution
  custom metrics with anomaly detection.
- **Composite alarm enhancements (2023-2024):** Extended rule syntax
  with NOT, nested AND/OR, INSUFFICIENT_DATA state references.
- **Logs Insights anomaly detection (2024-2025):** Anomaly detection
  for log-based metrics.
- **Contributor Insights integration (2025-2026):** Automatically
  surfaces top contributors when an anomaly is detected.
