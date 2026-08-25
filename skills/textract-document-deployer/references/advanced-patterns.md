# Advanced Patterns — Textract Document Deployer

Edge-case catalog and recent-feature notes moved verbatim from SKILL.md. Loaded on demand.

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **Queries feature GA (2023-2024):** Natural-language question
  answering on forms. More flexible than FORMS key-value extraction
  for variable-layout documents. Available in both sync
  (AnalyzeDocument) and async (StartDocumentAnalysis) APIs.

- **Signatures feature GA (2023-2024):** Bounding-box detection of
  signatures on documents. Available via AnalyzeDocument with
  FeatureTypes=["SIGNATURES"].

- **Expense Analysis improvements (2023-2024):** Enhanced vendor name
  and line-item extraction accuracy. OutputConfig now supports
  structured CSV outputs for queries and tables.

- **Lending Analysis (2023-2024):** Specialized async API
  (StartLendingAnalysis) for mortgage and lending documents
  (pay stubs, W-2s, 1099s, bank statements).

- **Layout feature (2023-2024):** AnalyzeDocument with
  FeatureTypes=["LAYOUT"] returns reading-order structural elements
  (titles, headers, footers, sections).

- **OutputConfig enhancements (2024-2025):** Per-page JSON output and
  structured CSV files (key-values, queries-results, tables) written
  directly to S3, reducing Get* pagination overhead.

- **European region expansion (2024-2025):** Textract available in
  additional EU regions (eu-west-3, eu-south-1, eu-north-1).

- **General Availability in APAC (2024-2025):** Textract GA in
  ap-southeast-3 (Jakarta) and ap-east-1 (Hong Kong), expanding
  options for APAC data-residency requirements.
