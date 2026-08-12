# Baseline (no-skill) — expense-analysis-invoices

> This is the response a model produces **without** the skill
> definition. It uses AnalyzeDocument FORMS for invoices (wrong —
> invoices/receipts have a purpose-built Expense API) and misses
> StartExpenseAnalysis, OutputConfig, and the KMS key policy
> requirements. Generated for with-skill-vs-baseline comparison.

---

Use AnalyzeDocument with FORMS and TABLES to extract the invoice
fields:

```bash
aws textract start-document-analysis \
  --document-location '{"S3Object":{"Bucket":"expense-input","Name":"batch-2026.pdf"}}' \
  --feature-types '["FORMS","TABLES"]'
```

You can parse the returned blocks to find vendor name, total, and
line items.
