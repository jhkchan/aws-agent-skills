# Eval prompt: already-optimized-macie

Optimise the following Amazon Macie deployment for cost. Walk all
optimization dimensions (discovery mode, frequency, buckets, sampling,
identifiers, suppression, delegation, export) and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

DeploymentId: macie-already-optimized-macie
Macie administrator: delegated (org-management)
Region: us-east-1

Automated discovery: ENABLED (covers all 12 business-data buckets)
Classification jobs: ONE_ONE_TIME only (ad-hoc investigation last
  quarter — no recurring targeted jobs)

managedDataIdentifierSelector: INCLUDE (PII + financial only)
Sampling: default (per-bucket ceiling)
Suppression rules: 3 active (access-logs prefix, public-assets
  prefix, known-safe-images prefix)
Classification export: ENABLED (S3 + Athena pipeline)
Bucket statistics: 12 buckets, 0 log/archive buckets in scope
  (all excluded via classification scope)

Cost Explorer (Service=Macie, last 30 days): $84.00
  (automated discovery incremental cost only)

Workload context: well-tuned Macie deployment. Monthly cost is
minimal and proportional to data churn. All log/archive buckets
excluded. Identifiers narrowed to compliance scope. Suppression
rules prevent known-safe re-evaluation.
