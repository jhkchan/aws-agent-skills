# Eval: data-stream-time-series

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — data stream for metrics-ds, 10 primary shards for 200 GB/day, data stream template with ILM rollover and tiering

## Prompt

Create a data stream for application metrics on domain search
-metrics-abc.us-east-1.es.amazonaws.com. Metrics include
timestamp, metric_name, value, and tags. Expected 200 GB per
day. 10 primary shards, 1 replica. Data stream name metrics-ds.
Create a data stream template with ILM integration for rollover
and tiering. Tags: Environment=production, DataType=metrics.
