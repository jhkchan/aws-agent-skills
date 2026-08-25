# Diagnostic Commands — Transcribe Job Deployer

Monitoring command listings moved verbatim from SKILL.md. Loaded on demand.

## Step 11 — CloudWatch metrics and billing alarm

Transcribe publishes metrics to CloudWatch for monitoring job
volume, duration, and errors.

| Metric | Description |
|---|---|
| `AudioDuration` | Total audio seconds processed (for billing) |
| `JobDuration` | Total processing time |
| `ThrottledCount` | Throttled requests |
| `JobFailureCount` | Failed jobs |

```bash
# Monitor audio duration processed (for cost tracking)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Transcribe \
  --metric-name AudioDuration \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 86400 \
  --statistics Sum \
  --dimensions Name=TranscriptionJob,Value=Batch

# Set a billing alarm for audio duration
aws cloudwatch put-metric-alarm \
  --alarm-name transcribe-duration-budget \
  --namespace AWS/Transcribe \
  --metric-name AudioDuration \
  --statistic Sum \
  --period 86400 \
  --threshold 288000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```
