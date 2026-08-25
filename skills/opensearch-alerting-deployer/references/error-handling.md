# Error handling — opensearch-alerting-deployer

Alerting failure-mode deep dives moved verbatim from SKILL.md (load on demand).

## Error handling

### Monitor creates but alerts never fire
- The trigger condition may never be met. Test the query manually
  in the OpenSearch DevTools console and verify it returns results
  satisfying the condition.

### Action fails at trigger time (SNS)
- The notification plugin (notification.yaml) is not configured at
  the domain level. Configure it with the SNS topic ARN and IAM
  role. Restart the alerting plugin if needed.

### Action fails at trigger time (webhook)
- The webhook URL is invalid or unreachable from the cluster.
  Verify network ACLs, security groups, and firewall rules.

### Anomaly detection produces no anomalies
- The detector may still be in cold start (training). Wait 15+
  minutes for training. Verify the detector is ingesting data by
  checking `last_update_time`.

### Alert storm (fires too frequently)
- Threshold too low or schedule too frequent. Increase threshold,
  reduce frequency, or add a deduplication window. Acknowledge
  active alerts via the `acks` API.

### Monitor execution is slow (cluster impact)
- Query too complex for schedule frequency. Use rollups or
  transforms to pre-aggregate. Increase the interval. Reduce the
  query time range.
