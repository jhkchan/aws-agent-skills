# Eval: windows-multiaz-ad-dedup

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Windows Multi-AZ, AD joined, dedup with estimated savings, shadow copies, DNS aliases, both subnets cited

## Prompt

Create an FSx for Windows file system in us-east-1. Multi-AZ
deployment, 1024 GB SSD storage, 32 MB/s throughput capacity.
Join to Managed AD directory d-aaa111222. VPC vpc-aaa11122,
subnets subnet-aaa111 (us-east-1a) and subnet-bbb222 (us-east-1b).
Enable dedup (GeneralPurpose). Enable shadow copies. DNS alias
fileshare.example.com. KMS encryption with AWS-managed key.
Backup: daily automatic, 7-day retention. Maintenance window:
Tuesday 01:00. Tags: Environment=production, ManagedBy=cloudops.
