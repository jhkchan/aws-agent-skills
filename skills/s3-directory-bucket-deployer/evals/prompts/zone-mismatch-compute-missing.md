# Eval prompt: zone-mismatch-compute-missing

Design a deployment plan for an S3 Express One Zone directory bucket.
Emit the standard VERDICT block (DIRECTORY_BUCKET_SPEC, VERDICT,
CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- Base bucket name: analytics-cache
- AZ: us-east-1a (resolve to AZ ID use1-az1)
- Region: us-east-1
- Compute: 6 x c7n.xlarge EC2 instances in subnet subnet-bbb
  (subnet-bbb is in use1-az2)
- Workload: real-time analytics cache
- SSE-S3 encryption
- Account: 111111111111

Additional context: the team deployed the directory bucket targeting
us-east-1a (AZ ID use1-az1) for single-digit-millisecond latency.
However, the EC2 instances were launched in subnet-bbb, which is in
use1-az2 — a different Availability Zone. The team has not yet noticed
the latency degradation or the cross-AZ transfer charges.
