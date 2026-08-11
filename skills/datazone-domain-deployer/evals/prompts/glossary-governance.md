# Eval: glossary-governance

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — comprehensive glossary with subscription policies (Public auto-approve through Restricted multi-level), Lambda auto-classification for PII tagging

## Prompt

Create a DataZone domain called governed-catalog in us-east-1,
account 111111111111. Project enterprise-data. Create glossary
terms: Public (auto-approve), Internal (project owner approval),
Confidential (data steward approval), Restricted (executive
multi-level approval). Configure Lambda-based metadata enrichment
function datazone-auto-classify to auto-tag assets with PII
classification based on column name patterns. S3 data source
enterprise-data-lake in account 222222222222. Tags:
Environment=production, Governance=enterprise.
