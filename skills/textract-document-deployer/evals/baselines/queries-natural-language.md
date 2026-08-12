# Baseline (no-skill) — queries-natural-language

> This is the response a model produces **without** the skill
> definition. It misses the QUERIES FeatureType requirement, the
> separate QueriesConfig block, and the OutputConfig pattern. Likely
> falls back to DetectDocumentText or AnalyzeDocument FORMS without
> realizing Queries is a distinct feature type. Generated for with-
> skill-vs-baseline comparison.

---

Run AnalyzeDocument with FORMS on the file:

```bash
aws textract analyze-document \
  --document '{"S3Object":{"Bucket":"forms-input","Name":"claims/2026-batch.pdf"}}' \
  --feature-types '["FORMS"]'
```

Then write custom code to find the policy number and claimant name in
the key-value pairs.
