# Eval prompt: zone-affinity-directory-bucket-ready

Design a deployment plan for an S3 Express One Zone directory bucket.
Emit the standard VERDICT block (DIRECTORY_BUCKET_SPEC, VERDICT,
CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- Base bucket name: ml-cache-data
- AZ: us-east-1a (resolve to AZ ID)
- Region: us-east-1
- Encryption: SSE-KMS with key
  arn:aws:kms:us-east-1:111111111111:key/abc-123
- Compute: 4 x c7n.large EC2 instances, already deployed in use1-az1
  (subnet subnet-aaa)
- Workload: ML training data cache (object-level reads/writes)
- No CRR, no versioning, no Object Lock needed
- Account: 111111111111

Additional context: the team is caching ML training shards for a
real-time inference pipeline. The directory bucket must deliver
single-digit-millisecond read latency from the same-AZ compute
instances. The workload is ephemeral cache data — durability beyond
a single AZ is acceptable.
