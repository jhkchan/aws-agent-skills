# Eval: tag-target-scheduled-association

**Difficulty:** hard
**Branch:** OPERATION_COMPLETED — tag targets (dynamic), rate(30 minutes) schedule, apply-at-creation, integer rate control (max-concurrency=10, max-errors=3), SSE-KMS output bucket

## Prompt

Create an SSM State Manager association named
PatchProductionFleet in us-east-1. Use document
AWS-ApplyPatchBaseline. Target instances tagged
Environment=production. Schedule rate(30 minutes). Run
immediately on creation. Allow 10 instances in parallel and stop
after 3 errors. Parameters: Operation=Install, SnapshotId=latest.
Route output to s3://my-ssm-output/ssm-output/ (bucket has
SSE-KMS with key arn:aws:kms:us-east-1:123456789012:key/abc123).
Tags: Environment=production, Owner=cloudops.
