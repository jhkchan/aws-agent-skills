# Neptune Graph Deployer — Diagnostic and Monitoring Commands

CloudWatch monitoring CLI and alert thresholds moved verbatim from SKILL.md.
Load on demand.

## CloudWatch metrics CLI (CPU utilization, storage growth)

```bash
# Monitor CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/Neptune \
  --metric-name EngineCPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=my-neptune-primary \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average

# Monitor graph storage growth
aws cloudwatch get-metric-statistics \
  --namespace AWS/Neptune \
  --metric-name VolumeBytesUsed \
  --dimensions Name=DBClusterIdentifier,Value=my-neptune-cluster \
  --start-time $(date -u -v-1D +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 --statistics Average
```

**Key metrics to alert on:**
- EngineCPUUtilization > 80% sustained → scale up or add replicas.
- BufferCacheHitRatio < 90% → graph working set exceeds memory; larger
  instance needed.
- VolumeBytesUsed approaching limit → storage scaling needed.
- GremlinErrorsPerSec > 0 → query errors or timeouts.
