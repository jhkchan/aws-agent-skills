# Eval: vpc-endpoint-only-access

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — StringNotEquals Deny on aws:SourceVpce vpce-0abc123def456, blocks all non-endpoint traffic

## Prompt

Restrict bucket "internal-data" in us-east-1 (account
123456789012) to only allow access through VPC endpoint
vpce-0abc123def456. Deny all traffic that does not come from
this endpoint. The bucket already has HTTPS-only enforced and
BPA enabled.
