# Eval prompt: express-one-zone-ml-model-serving-latency

Optimise the S3 workload described below. Walk the workload-driven
optimisation tree and emit the standard optimisation block (TARGET,
VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: We have an ML inference service that loads model weights from
S3 on each cold start. The model file is ~200 MB. p99 FirstByteLatency
on standard S3 is ~80 ms; our service target is <10 ms p99. Cold-start
latency is dominated by the S3 GET.

```text
Bucket: express-one-zone-ml-model-serving-latency-models
Region: us-east-1
Workload: low-latency model-weight read
ObjectSize: 200 MB
AccessPattern: 1 GET per cold start (~100 cold starts per minute)
ClientGeography: us-east-1 EC2 (inf1.xlarge)
TargetLatency: <10 ms p99 FirstByteLatency
AvailabilityTolerance: can tolerate single-AZ risk if paired with
  cross-region replication

Current bucket: standard S3 (us-east-1, multi-AZ)

CloudWatch metrics:
  - FirstByteLatency p99: 80 ms
  - TotalRequestLatency p99: 95 ms
  - 4xxErrors: 0
  - 5xxErrors: 0
```

Standard S3 cannot meet the <10 ms target — it is bounded by the
multi-AZ replication and shared infrastructure. S3 Express One Zone
uses directory buckets and delivers single-digit-ms p99 for both reads
and writes; the trade-off is single-AZ availability.
