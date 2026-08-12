# Eval prompt: cloudtrail-lake-scoping

Optimise the following CloudTrail configuration for cost. Walk the
CloudTrail Lake scoping decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

TrailName: trail-cloudtrail-lake-scoping
IsOrganizationTrail: true
IsMultiRegionTrail: true
IncludeManagementEvents: true
Status: RUNNING

CloudTrail Lake Event Data Store:
  - EDS ID: 7a7b8c9d-0e1f-2345-6789-0123456789ab
  - Name: org-audit-eds
  - Event categories ingested: Management, Data
  - Retention: 90 days
  - Monthly ingestion: 100 GB
    - Management events: 8 GB/month (8%)
    - Data events: 92 GB/month (92%)
  - Use case: IAM access pattern analysis (management events only)

Region: us-east-1
