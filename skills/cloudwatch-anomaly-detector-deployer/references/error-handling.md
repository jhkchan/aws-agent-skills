# Error Handling — CloudWatch Anomaly Detection Deployer

Error-handling deep dive moved out of the SKILL.md body for progressive disclosure: failure modes, root causes, and remedies. Loaded on demand by the skill.

---

## Error handling

### Detector stuck in LEARNING state
- The metric does not have enough historical data points. Verify with
  `get-metric-statistics` that at least 15 data points exist at the
  configured period. If the metric is new, wait for more data to
  accumulate. Also check that the namespace, metric name, and
  dimensions match the actual metric exactly.

### Alarm in INSUFFICIENT_DATA
- The detector has not reached TRAINED state, or the metric is not
  producing data. Check the detector state with
  `describe-anomaly-detectors`. If TRAINED, check the alarm's metric
  math expression for errors. Verify the SNS topic exists.

### Too many false positive alarms
- The std dev multiplier is too low for the metric's natural
  variability. Increase the multiplier (3 → 4) and wait for the model
  to re-train (up to 15 minutes). Also consider increasing
  evaluation-periods (3 → 5) for more sustained anomaly detection.

### Anomaly alarm never fires
- Possible causes: (1) detector in LEARNING state (not enough data),
  (2) std dev multiplier too high (band too wide), (3) alarm metric
  math expression is wrong, (4) SNS topic not configured. Check each
  in order.

### Cross-account detector sees no data
- The source account has not enabled sharing, or the monitoring
  account does not have the correct data source link. Verify the
  resource policy in the source account and the link in the monitoring
  account.
