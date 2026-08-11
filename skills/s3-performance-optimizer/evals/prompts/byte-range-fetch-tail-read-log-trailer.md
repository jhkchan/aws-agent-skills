# Eval prompt: byte-range-fetch-tail-read-log-trailer

Optimise the S3 workload described below. Walk the workload-driven
optimisation tree and emit the standard optimisation block (TARGET,
VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: We have an analytics service that reads only the last 1 KB of
large S3 log files to extract the trailer offset. Each log file is
~5 GB. The current client code uses GET object (full download) and
parses the trailer locally. Reads take ~40 seconds; we want them
under 100 ms.

```text
Bucket: byte-range-fetch-tail-read-log-trailer-archive
Region: us-east-1
Workload: read-tail-of-large-object
ObjectSize: 5 GB
AccessPattern: read last 1 KB only (trailer offset lookup)
ClientGeography: us-east-1 EC2
TargetLatency: <100 ms per read

Current read code:
  response = s3.get_object(
      Bucket='byte-range-fetch-tail-read-log-trailer-archive',
      Key='logs/2026/08/10/app.log')
  body = response['Body'].read()  # downloads all 5 GB
  trailer = body[-1024:]

CloudWatch metrics:
  - FirstByteLatency p99: 45 ms (per-request)
  - BytesDownloaded per request: ~5 GB
  - TotalRequestLatency p99: 40 s (driven by full-body download)
```

The access pattern only needs the last 1 KB; the client is downloading
5 GB to discard 99.99998% of it. S3 byte-range fetch (`Range:
bytes=-1024`) returns the tail in single-digit ms regardless of object
size.
