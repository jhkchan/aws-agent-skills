# Eval prompt: recurring-to-automated-discovery

Optimise the following Amazon Macie deployment for cost. Walk the
discovery-mode decision framework (automated vs targeted) and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

DeploymentId: macie-recurring-to-automated-discovery
Macie administrator: delegated (org-management)
Region: us-east-1

Classification jobs (last 30 days):
  - jobId: job-targeted-pci-scan
    jobType: SCHEDULED (daily, 30 runs/month)
    buckets: [data-lake-raw, data-lake-curated, data-lake-enriched,
              access-logs-prod, cloudtrail-archive, public-assets,
              backup-tier-1, backup-tier-2, ml-feature-store,
              user-uploads, pii-quarantine, finance-reports,
              hr-records, app-configs, system-buckets, temp-staging,
              analytics-output, report-snapshots]
    managedDataIdentifierSelector: ALL
    sampling: default (per-bucket ceiling)
    jobsRun: 30
    bytesProcessed: 37,200,000,000,000 (37.2 TB cumulative)
    objectsProcessed: 480,000,000

Automated discovery: ENABLED but scope excludes access-logs

Cost Explorer (Service=Macie, last 30 days): $37,210.00

Bucket statistics: 18 buckets total, 4 are log/archive
(access-logs-prod, cloudtrail-archive, public-assets,
backup-tier-1), 2 are known-safe validated clean.

Workload context: stable S3 data lake with ~5% monthly churn.
PCI compliance scope; only financial and credentials identifiers
are required. No daily compliance mandate; monthly cadence
acceptable.
