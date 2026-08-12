# Eval prompt: scan-frequency-reduction

Optimise the following Amazon Macie deployment for cost. Walk the scan-
frequency decision framework (weekly vs monthly for a quarterly
compliance window) and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DeploymentId: macie-scan-frequency-reduction
Macie administrator: delegated (org-management)
Region: us-east-1

Classification jobs (last 30 days):
  - jobId: job-weekly-compliance-scan
    jobType: SCHEDULED (weekly, 4 runs/month)
    buckets: [data-lake-curated, pii-repository, finance-reports]
    managedDataIdentifierSelector: INCLUDE (PII + financial)
    sampling: default
    jobsRun: 4
    bytesProcessed: 8,000,000,000,000 (8 TB cumulative)
    objectsProcessed: 120,000,000

Automated discovery: DISABLED (compliance team prefers targeted jobs)

Cost Explorer (Service=Macie, last 30 days): $800.00

Bucket statistics: 3 buckets, all high-risk regulated data.
Quarterly compliance window — no daily or weekly mandate.

Workload context: HIPAA compliance scope. Targeted jobs are
required by compliance policy (cannot switch to automated
discovery). Frequency reduction from weekly to monthly is
acceptable per the compliance officer's written sign-off.
