# Eval prompt: prefix-distribution-hot-shard-503-throttling

Optimise the S3 workload described below. Walk the workload-driven
optimisation tree and emit the standard optimisation block (TARGET,
VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: S3 bucket `prefix-distribution-hot-shard-503-throttling-prod`
receives ~15,000 PUT/sec from a fleet of ingest workers. All keys are
written under a single date-based prefix (`yyyy/MM/dd/`). CloudWatch
shows sustained 503 errors during peak; application logs show
`SlowDown` exceptions.

```text
Bucket: prefix-distribution-hot-shard-503-throttling-prod
Region: us-east-1
Workload: write-heavy telemetry ingest
RequestRate: 15,000 PUT/sec (peak)
AvgObjectSize: 12 KB
KeyPattern: telemetry/2026/08/10/<uuid>.json
  (all keys under one yyyy/MM/dd prefix)
ClientGeography: us-east-1 EC2 (fleet of 200 instances)
TargetLatency: 0 throttling at peak

CloudWatch metrics (last hour, peak window):
  - 5xxErrors Sum: 2,400 (SlowDown responses)
  - 4xxErrors Sum: 0
  - PutRequests Sum: 54M (~15,000/sec sustained)
  - BytesUploaded: ~650 GB

Current prefix layout: single date-based prefix; no hash distribution.
```

Although S3 removed the 3,500/5,500 per-second per-prefix cap in July
2023 for most workloads, request rates above ~10,000/sec on a single
prefix can still benefit from hash-based prefix sharding. The current
single-date prefix concentrates all 15,000 PUT/sec onto one partition.
