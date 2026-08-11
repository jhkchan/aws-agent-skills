# Eval: lustre-persistent-s3-export

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Lustre PERSISTENT_1, S3 data repository linked (import/export), LZ4 compression, auto-import policy configured

## Prompt

Create an FSx for Lustre file system in us-east-1. PERSISTENT_1
deployment, 2400 GB SSD storage, 1000 MB/s/TB throughput. S3
export from s3://my-hpc-bucket/data with auto-import policy
NEW_CHANGED. LZ4 compression. VPC vpc-ccc33344, subnet
subnet-ccc333 (us-east-1a). Tags: Environment=production,
Workload=hpc.
