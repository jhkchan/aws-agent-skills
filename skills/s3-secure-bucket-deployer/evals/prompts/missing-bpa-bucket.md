# Eval: missing-bpa-bucket

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — bucket exists but lacks BPA and ownership controls

## Prompt

We created a bucket "legacy-app-data" last year and just realized
it has no Block Public Access configured, no Object Ownership
setting, and no bucket policy. It does have SSE-S3 default
encryption and versioning. Help me get this to production-ready
security baseline. Region: us-west-2, Account: 123456789012.
