# Sensitivity Tuning — CloudWatch Anomaly Detection Deployer

Deep reference on standard deviation multiplier tuning, band width
calibration, assessment period selection, and the iterative tuning
workflow. Loaded on demand by the skill — kept out of the main SKILL.md
body so the provisioning procedure stays scannable.

## Standard deviation multiplier fundamentals

### What the std dev multiplier controls

The standard deviation multiplier (`StandardDeviation` in the detector
configuration JSON) directly controls the width of the anomaly
detection band. The ML model computes the expected value of the metric
and its standard deviation (sigma). The band boundaries are:

```text
Upper band = expected_value + (std_dev_multiplier × sigma)
Lower band = expected_value - (std_dev_multiplier × sigma)
```

A higher multiplier produces a wider band (less sensitive); a lower
multiplier produces a narrower band (more sensitive).

### The sigma probability table

Assuming normally distributed residuals (which is approximately true
for most well-behaved metrics):

| Std dev multiplier | Band captures | Outside band (anomalous) | False positive rate |
|---|---|---|---|
| 1.0 | ~68% of data | ~32% | Very high (~1 in 3 points) |
| 1.5 | ~87% of data | ~13% | High |
| 2.0 | ~95% of data | ~5% | Moderate (1 in 20) |
| 2.5 | ~98.8% of data | ~1.2% | Low |
| 3.0 (DEFAULT) | ~99.7% of data | ~0.3% | Very low (1 in 370) |
| 4.0 | ~99.994% of data | ~0.006% | Minimal |
| 5.0 | ~99.99994% of data | ~0.00006% | Near zero |

**Note:** real-world metrics are rarely perfectly normal. The actual
false positive rate may differ from the theoretical values above. Use
the table as a guide, not a guarantee.

## Tuning workflow

### Phase 1: Initial deployment (weeks 1-2)

1. Deploy with default std dev multiplier (3).
2. Set evaluation-periods to 3 (balanced).
3. Observe for one full week (captures a weekly cycle).
4. Count false positives and missed anomalies.

```bash
# Review alarm history after one week
aws cloudwatch describe-alarm-history \
  --alarm-name "cpu-anomaly-breach-i-abc123" \
  --history-item-type StateUpdate \
  --start-date $(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ) \
  --end-date $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --region us-east-1 \
  --query 'AlarmHistoryItems[*].{Timestamp:TimestampSummary,Summary:HistorySummary}' \
  --output table
```

### Phase 2: Tuning (weeks 3-4)

Based on Phase 1 observations:

| Observation | Action |
|---|---|
| Too many false positives (>5/week) | Increase std dev: 3 → 4 |
| Missing real anomalies | Decrease std dev: 3 → 2 |
| Both false positives AND missed anomalies | Increase evaluation-periods: 3 → 5 |
| Alarm flaps rapidly | Increase evaluation-periods; also check period length |

```bash
# Tune std dev to 4 (less sensitive)
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/EC2" \
  --metric-name "CPUUtilization" \
  --dimensions Name=InstanceId,Value=i-abc1234567890 \
  --stat "Average" \
  --period 300 \
  --configuration '{"StandardDeviation": 4}'
```

### Phase 3: Steady state (week 5+)

Once the tuning stabilizes:
- Review monthly for metric pattern shifts (e.g., traffic growth).
- Re-tune if the metric's baseline pattern changes significantly (e.g.,
  new feature launch changes traffic patterns).
- Consider composite alarms for layered sensitivity (anomaly at std dev
  2 OR static threshold for critical coverage).

## Assessment period (evaluation-periods) interaction

The assessment period on the alarm interacts with the std dev
multiplier. A lower std dev can be compensated by a higher evaluation
period:

```text
Tuning combinations (example for CPU anomaly):
  ├── std dev 2, evaluation-periods 1 → Very sensitive (fast, noisy)
  ├── std dev 2, evaluation-periods 3 → Sensitive (balanced for volatile)
  ├── std dev 3, evaluation-periods 3 → DEFAULT (balanced, recommended)
  ├── std dev 3, evaluation-periods 5 → Less sensitive (sustained anomalies only)
  ├── std dev 4, evaluation-periods 2 → Less sensitive (wide band, quick to fire)
  └── std dev 4, evaluation-periods 5 → Very conservative (only major sustained)
```

**Key insight:** the combination of std dev and evaluation-periods
determines the overall sensitivity profile. Tune both together, not
independently.

## Metric-specific tuning recommendations

### CPUUtilization
- Std dev: 3 (default)
- Evaluation-periods: 3
- Period: 300 (5 min)
- Stat: Average
- Notes: CPU follows diurnal patterns; default works well for most
  instances. Increase std dev for batch-processing instances.

### MemoryUtilization (custom metric)
- Std dev: 3
- Evaluation-periods: 3
- Period: 300
- Stat: Average
- Notes: Similar to CPU. Watch for memory leak patterns (gradual
  increase) which anomaly detection may not flag if the band expands.

### RequestCount / RequestCountPerTarget
- Std dev: 3
- Evaluation-periods: 2
- Period: 60 (1 min)
- Stat: Sum
- Notes: Traffic patterns are well-suited for anomaly detection. Use
  shorter period for faster detection.

### TargetResponseTime (latency)
- Std dev: 2 (more sensitive — latency spikes indicate problems)
- Evaluation-periods: 2
- Period: 60
- Stat: p99 or p99.9 (tail latency)
- Notes: Latency is volatile; lower std dev catches issues faster.

### DatabaseConnections
- Std dev: 3
- Evaluation-periods: 3
- Period: 300
- Stat: Average
- Notes: Connection patterns follow application traffic. Watch for
  connection pool exhaustion (sudden spike).

### Error rate (custom metric)
- Std dev: NOT RECOMMENDED
- Alternative: Use static threshold (> 0 or > N%)
- Notes: Error rates are often sparse (mostly zero). Anomaly detection
  struggles with sparse data. Use static thresholds instead.

## Verifying band quality

After deployment, verify the band quality by comparing the expected
band to actual metric values over the historical period:

```bash
# Get the anomaly band values for the last 24 hours
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/EC2","MetricName":"CPUUtilization","Dimensions":[{"Name":"InstanceId","Value":"i-abc1234567890"}]},"Period":300,"Stat":"Average"}},
    {"Id":"e1","Expression":"ANOMALY_DETECTION_BAND(m1)","Label":"Band"}
  ]' \
  --start-time $(date -u -v-1d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --region us-east-1 \
  --query 'MetricDataResults[*].{Id:Id,Values:Values}' --output table
```

If the band is consistently too tight (many points outside) or too
loose (band never breached even during known incidents), adjust the
std dev multiplier accordingly.
