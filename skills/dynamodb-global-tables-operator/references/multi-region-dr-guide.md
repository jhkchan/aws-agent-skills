# Multi-Region Disaster Recovery Guide — DynamoDB Global Tables

Supplementary reference for the DynamoDB Global Tables Operator skill.
Covers DR planning, RTO/RPO analysis, failover runbooks, and LWW
conflict mitigation.

## RTO and RPO analysis

| Metric | Value | Notes |
|---|---|---|
| **RTO (Recovery Time Objective)** | Seconds to minutes | Application SDK detects failure and switches regions. No data restore needed. |
| **RPO (Recovery Point Objective)** | Near-zero | Replication is asynchronous but typically < 1 second. Last-second writes may be lost if the region fails mid-replication. |
| **Failback RTO** | Minutes | Switching back to the original region after recovery. |
| **Failback RPO** | Zero | Data replicated back to the recovered region automatically. |

**Key distinction from snapshot-based DR:** Global Tables provide
continuous replication with near-zero RPO. Snapshot-based DR (AWS
Backup, PITR restore) has RPO = snapshot interval (minutes to hours)
and RTO = restore time (minutes to hours). Global Tables is the
superior DR strategy for mission-critical workloads.

## Failover runbook

### 1. Detection

- **CloudWatch alarm:** `ReplicationLatency` spikes, or the application
  reports DynamoDB errors from a specific region.
- **AWS Health Dashboard:** regional service degradation confirmed.
- **Application health check:** the application's DynamoDB client
  reports connection timeouts or 5xx errors from the region.

### 2. Decision

| Condition | Action |
|---|---|
| Transient errors (retryable) | SDK retry policy handles automatically — no failover |
| Sustained errors (> 30 seconds) | Trigger failover to the next healthy region |
| AWS Health Dashboard confirms regional outage | Trigger failover immediately |
| Single-AZ issue within a region | No failover needed — DynamoDB is multi-AZ |

### 3. Failover execution

**Option A: SDK-level (recommended, fastest RTO)**

The application SDK should be pre-configured with:
```python
# AWS SDK v2 with region switching
client = boto3.client('dynamodb',
    region_name='us-east-1',
    config=Config(
        retries={'max_attempts': 3, 'mode': 'adaptive'},
        region_switching=True  # auto-switch on regional failure
    ))
```

**Option B: Route 53 health check failover**

- Primary record: DynamoDB endpoint in us-east-1.
- Failover record: DynamoDB endpoint in us-west-2.
- Health check interval: 10 seconds.
- Route 53 switches DNS automatically.

**Option C: Manual switch**

1. Confirm the target region is ACTIVE.
2. Update the application configuration (env var, Parameter Store,
   Secrets Manager) to point to the new region.
3. Restart or reload the application to pick up the new endpoint.

### 4. Post-failover verification

1. Verify writes succeed in the new region.
2. Verify reads reflect the latest data.
3. Monitor ReplicationLatency to other regions.
4. Monitor for LWW conflicts.

### 5. Failback (after the degraded region recovers)

1. AWS Health Dashboard confirms the region is operational.
2. Verify ReplicationLatency to the recovered region returns to normal.
3. Switch the application back (SDK, Route 53, or manual).
4. Audit for LWW conflicts: compare item versions across regions.

## LWW conflict mitigation

Global Tables v2 uses `LAST_WRITER_WINS`. Conflicts occur when the
same item is written in two regions within the replication window
(< 1 second). The later-timestamp write wins.

### Conflict-prone patterns

| Pattern | Risk | Mitigation |
|---|---|---|
| Counter increments from multiple regions | HIGH — lost updates | Use DynamoDB Streams to merge; or single-region writes for counters |
| Same user session active in two regions | MEDIUM — session overwrite | Pin sessions to a region (geo-routing) |
| Bulk import from multiple regions | HIGH — overwrite race | Import from one region only |
| Status updates from multiple regions | MEDIUM — last status wins | Acceptable if LWW semantics are OK for the use case |

### Conflict audit procedure

After a failover and failback:

```bash
# 1. Export both regions' data to S3.
aws dynamodb export-table-to-point-in-time \
  --table-name orders-prod --region us-east-1 \
  --s3-bucket dr-audit-bucket --export-format DYNAMODB_JSON \
  --export-time 2026-08-09T12:00:00Z

aws dynamodb export-table-to-point-in-time \
  --table-name orders-prod --region us-west-2 \
  --s3-bucket dr-audit-bucket --export-format DYNAMODB_JSON \
  --export-time 2026-08-09T12:00:00Z

# 2. Compare item counts and spot-check high-traffic items.
# Use Athena or a Spark job to diff the exports.
```

## DR drill checklist

- [ ] Document the failover runbook and test it quarterly.
- [ ] Verify the SDK retry policy is configured for region switching.
- [ ] Verify Route 53 health checks (if using DNS failover).
- [ ] Enable PITR on ALL replica regions.
- [ ] Set CloudWatch alarms on ReplicationLatency for each region pair.
- [ ] Test failover in a staging global table before production.
- [ ] Document which region is the "primary" for each application.
- [ ] Verify autoscaling policies are registered in all regions.
- [ ] Test failback after the drill.
- [ ] Audit for LWW conflicts after the drill.
