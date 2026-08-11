# Eval: vpc-only-team-ap

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — VPC origin + through-AP Deny + per-AP BPA

## Prompt

Provision a VPC-only access point for bucket "prod-shared-data"
(account 123456789012, region us-east-1) so that Team A's role
"arn:aws:iam::123456789012:role/TeamARole" can read/write only
the "team-a/" prefix. AP name: "team-a-vpc-ap". VPC ID:
vpc-0abc123def456. Bucket baseline (BPA, SSE-KMS, versioning)
already verified. Include per-AP Block Public Access and the
bucket policy that blocks the global hostname bypass.
