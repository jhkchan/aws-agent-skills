# Baseline (no-skill) — async-forms-tables-sns-kms

> This is the response a model produces **without** the skill
> definition. It lists a CLI command but reaches for
> DetectDocumentText (the wrong API for a 1450-page PDF), misses the
> sync-vs-async distinction, the OutputConfig requirement, the KMS
> key policy grant to the Textract service principal, and the SNS
> notification role trust relationship. Generated for with-skill-vs-
> baseline comparison.

---

Call DetectDocumentText on the file:

```bash
aws textract detect-document-text \
  --document '{"S3Object":{"Bucket":"doc-input","Name":"invoices/2026-q3.pdf"}}'
```

That should return the extracted text.
