# Eval: batch-inference-s3

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — batch inference job, S3 JSON Lines input, S3 output, numResults=25

## Prompt

Set up a Personalize batch inference job in us-east-1 for the
user-personalization-solution solution version
arn:aws:personalize:us-east-1:123456789012:solution-version/abc123.
Score the user list at s3://batch-input/users.json (JSON Lines).
Write 25 recommendations per user to s3://batch-output/recs/. Role
arn:aws:iam::123456789012:role/PersonalizeBatchRole.
