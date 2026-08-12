# Eval prompt: custom-identifier-and-suppression

Optimise the following Amazon Macie deployment for cost. Walk the
custom-identifier audit (consolidate overlaps, remove unused, audit
regex performance) and suppression-rule (cut known-safe re-evaluation)
decision frameworks and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DeploymentId: macie-custom-identifier-and-suppression
Macie administrator: delegated (org-management)
Region: us-east-1

Automated discovery: ENABLED
Custom data identifiers: 12 configured
  (including 3 overlapping SSN variants, 2 overlapping credit-card
  patterns, 1 regex with nested quantifiers causing backtracking,
  4 identifiers with zero matches in 90 days)

Managed data identifier selector: INCLUDE (PII only)

Findings (last 30 days):
  - 2,400 findings, 2,100 from the same prefix
    (s3://data-lake/public-assets/) which has been validated
    as known-safe public marketing collateral
  - 0 suppression rules currently configured

Cost Explorer (Service=Macie, last 30 days): $1,240.00
  (elevated due to custom identifier evaluation overhead and
  re-evaluation of known-safe prefix)

Bucket statistics: 15 buckets, all business data.
Workload context: marketing company with public brand assets
stored in data-lake/public-assets/. The public-assets prefix has
been validated by the data governance team as containing only
public marketing collateral (images, videos, PDFs).
