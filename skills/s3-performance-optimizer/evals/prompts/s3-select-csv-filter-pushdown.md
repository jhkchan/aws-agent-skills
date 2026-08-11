# Eval prompt: s3-select-csv-filter-pushdown

Optimise the S3 workload described below. Walk the workload-driven
optimisation tree and emit the standard optimisation block (TARGET,
VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: We have a daily analytics job that processes 100 GB of CSV
exports. The job downloads the full CSV from S3 and filters client-side
for records where `amount > 1000` (about 5% of records match). The job
takes ~3 hours; the network transfer dominates. We want it under 30
minutes.

```text
Bucket: s3-select-csv-filter-pushdown-warehouse
Region: us-east-1
Workload: full-scan CSV with filter predicate
ObjectSize: 100 GB per file
Selectivity: ~5% of records match the filter
ClientGeography: us-east-1 EC2 (c5.2xlarge)
TargetThroughput: complete job in <30 min

Current pipeline (Python + boto3):
  obj = s3.get_object(
      Bucket='s3-select-csv-filter-pushdown-warehouse',
      Key='exports/2026-08-10.csv')
  reader = csv.reader(obj['Body'].iter_lines())
  matches = [r for r in reader if float(r[2]) > 1000]

CloudWatch metrics:
  - BytesDownloaded per job: ~100 GB
  - GET count per job: 1
  - TotalRequestLatency: ~3 hours (transfer-bound)
```

The workload is a full-scan of CSV with a server-side pushdown-able
predicate. S3 Select (`select-object-content`) would push the filter
into S3, reducing transfer 10-20x at 5% selectivity.
