# Eval: mrap-two-region-active-active

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — MRAP active-active with explicit non-backfill warning

## Prompt

Build a Multi-Region Access Point "global-assets-mrap" over
buckets "assets-use1" (us-east-1) and "assets-usw2"
(us-west-2). Account: 123456789012. Both buckets have versioning
enabled and SSE-KMS. Tell me how to verify and warn me about the
backfill limitation.
