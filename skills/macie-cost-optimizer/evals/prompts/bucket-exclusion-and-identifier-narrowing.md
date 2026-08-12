# Eval prompt: bucket-exclusion-and-identifier-narrowing

Optimise the following Amazon Macie deployment for cost. Walk the
bucket-selection (exclude log/archive/system) and identifier-scope
(managed selector narrowing) decision frameworks and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

DeploymentId: macie-bucket-exclusion-and-identifier-narrowing
Macie administrator: delegated (org-management)
Region: us-east-1

Classification jobs (last 30 days):
  - jobId: job-automated-discovery-weekly
    jobType: SCHEDULED (weekly)
    buckets: 20 buckets in scope
      (including access-logs-prod, cloudtrail-archive,
      alb-logs, s3-server-access, system-buckets-aws,
      temp-staging-ephemeral)
    managedDataIdentifierSelector: ALL
    sampling: default
    jobsRun: 4
    bytesProcessed: 4,800,000,000,000 (4.8 TB cumulative)

Automated discovery: ENABLED

Cost Explorer (Service=Macie, last 30 days): $480.00

Bucket statistics: 20 buckets, 6 are log/archive/system,
14 are business data. Compliance regime: GDPR (EU personal data
identifiers only required). Prior Macie runs on the 6 log/archive
buckets returned zero findings.

Workload context: GDPR PII detection. Only personal data
identifiers are required; financial and credentials categories
are not in scope. The 6 log/archive/system buckets have been
validated clean by the data governance team.
