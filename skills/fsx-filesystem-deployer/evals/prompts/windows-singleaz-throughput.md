# Eval: windows-singleaz-throughput

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Windows Single-AZ, throughput stepped to 256 MB/s (nearest step above 180 MB/s with headroom), HDD storage

## Prompt

Create an FSx for Windows file system in us-east-1. Single-AZ
deployment, 512 GB HDD storage. Join to Managed AD directory
d-aaa111222. VPC vpc-aaa11122, subnet subnet-aaa111 (us-east-1a).
The workload needs approximately 180 MB/s throughput. Tags:
Environment=dev, ManagedBy=cloudops.
