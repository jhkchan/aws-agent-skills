# Eval: expense-analysis-invoices

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — async StartExpenseAnalysis (purpose-built for invoices/receipts), not AnalyzeDocument FORMS

## Prompt

Process a 600-page batch of invoices and receipts at
s3://expense-input/batch-2026.pdf in us-east-1 using Textract. I need
vendor names, totals, and line items. Output to
s3://expense-output/results/. Same region. KMS key
arn:aws:kms:us-east-1:123456789012:key/efgh5678.... SNS topic
arn:aws:sns:us-east-1:123456789012:ExpenseComplete. Role
arn:aws:iam::123456789012:role/ExpenseRole.
