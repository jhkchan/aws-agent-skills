# Eval: oai-to-oac-migration

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — add OAC alongside OAI, update bucket policy with both grants, update distribution, verify, then remove OAI

## Prompt

Migrate distribution E3EXAMPLE3XXX from Origin Access Identity
(OAI E3OAIID1234) to Origin Access Control. S3 bucket is
my-legacy-bucket in us-east-1, account 111122223333. The OAI
canonical user ID is 1a2b3c4d5e6f7g8h9i0j. Need zero downtime.
Tags: Environment=production, Migration=oai-to-oac.
