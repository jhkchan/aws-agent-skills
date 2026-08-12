# Eval: multi-region-dr-with-lifecycle

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — replication to us-west-2 and ap-southeast-2, lifecycle policies in all regions, 3x storage cost noted, replication lag awareness for large images

## Prompt

Configure ECR replication from us-east-1 (account
111122223333) to us-west-2 and ap-southeast-2. We have
large images (2-5GB) and need cost control. Apply lifecycle
policies to retain only the last 30 images per repo in all
regions. Tags: Environment=production, Pattern=multi-region-dr.
