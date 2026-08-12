# Eval: queries-natural-language

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — async StartDocumentAnalysis with QUERIES FeatureType and QueriesConfig block containing three user-supplied questions

## Prompt

Use Textract on a 320-page forms PDF at
s3://forms-input/claims/2026-batch.pdf in us-east-1. I need the
Queries feature to ask: "What is the policy number?", "What is the
claimant name?", and "What is the date of loss?". Write results to
s3://forms-output/queries/ (same region). No KMS, no SNS. Account
123456789012. Role arn:aws:iam::123456789012:role/TextractQueriesRole.
