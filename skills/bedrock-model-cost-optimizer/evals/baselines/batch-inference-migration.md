# Baseline (no-skill) response: batch-inference-migration

This file captures what a generic assistant produces WITHOUT the
bedrock-model-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, 50% batch discount math,
S3 I/O setup, dollar savings estimate, CONFIRM gate).

---

Your bulk document summarisation workload is processing 500,000
documents per month using real-time API calls. Since this is a nightly
batch job with no user waiting for results, you could use the Bedrock
Batch API instead.

The Batch API gives you a 50% discount on both input and output tokens
compared to on-demand pricing. Since you're spending about $500/month,
this would save you roughly $250/month.

You can create a batch job like this:

```bash
aws bedrock create-model-invocation-job \
  --job-name "nightly-summarisation" \
  --model-id "anthropic.claude-3-haiku-20240307-v1:0" \
  --input-data-config '{"s3InputDataConfig": {"s3Uri": "s3://bucket/input/"}}' \
  --output-data-config '{"s3OutputDataConfig": {"s3Uri": "s3://bucket/output/"}}'
```

The job will process all your documents and write results to S3. It
might take a few hours but since it's overnight that should be fine.
