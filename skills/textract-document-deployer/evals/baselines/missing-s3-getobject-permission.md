# Baseline (no-skill) — missing-s3-getobject-permission

> This is the response a model produces **without** the skill
> definition. It emits the StartDocumentAnalysis command without
> checking the IAM policy for s3:GetObject on the input bucket. The
> command fails at runtime with InvalidS3Object or AccessDenied —
> the missing permission is silently ignored at provisioning time.
> Generated for with-skill-vs-baseline comparison.

---

Run StartDocumentAnalysis:

```bash
aws textract start-document-analysis \
  --document-location '{"S3Object":{"Bucket":"doc-input","Name":"invoices/2026-q3.pdf"}}' \
  --feature-types '["FORMS","TABLES"]' \
  --output-config '{"S3Bucket":"doc-output","S3Prefix":"textract/"}' \
  --region us-east-1
```

This should return a JobId you can poll.
