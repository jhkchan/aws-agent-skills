# Diagnostic Commands (load on demand) — CloudWatch Metric Stream Deployer

Metric stream lifecycle API operations moved verbatim from SKILL.md. Load on demand when inspecting, pausing, or deleting a stream.


---

## Step 10 — CloudWatch API operations (table + lifecycle CLI) (moved from SKILL.md)

| API | Purpose |
|---|---|
| `PutMetricStream` | Create a new metric stream |
| `GetMetricStream` | Retrieve a metric stream's configuration |
| `ListMetricStreams` | List all metric streams in the region |
| `DeleteMetricStream` | Delete a metric stream |
| `StartMetricStreams` | Resume a stopped stream |
| `StopMetricStreams` | Temporarily stop a stream (billing pauses) |

```bash
# Get stream configuration
aws cloudwatch get-metric-stream --name "ProductionMetricStream" --region us-east-1

# List all streams
aws cloudwatch list-metric-streams --region us-east-1

# Stop a stream (pause billing)
aws cloudwatch stop-metric-streams --names "ProductionMetricStream" --region us-east-1

# Delete a stream
aws cloudwatch delete-metric-stream --name "ProductionMetricStream" --region us-east-1
```
