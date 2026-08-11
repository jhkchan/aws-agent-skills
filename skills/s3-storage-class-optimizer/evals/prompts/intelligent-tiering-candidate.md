# Eval prompt: intelligent-tiering-candidate

Optimise the following S3 bucket for storage cost. Walk the storage-class
analysis framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

BucketName: bucket-intelligent-tiering-candidate
Region: us-east-1
Storage (total): 20 TB
Storage class distribution:
  - Standard: 20 TB (100%)
Versioning: Suspended
Lifecycle policy: none
Intelligent-Tiering: not configured
Storage Lens (last 30 days):
  - Objects aged 0-30 days: 8 TB
  - Objects aged 31-90 days: 4 TB
  - Objects aged 91-180 days: 3 TB
  - Objects aged 181-365 days: 3 TB
  - Objects aged >365 days: 2 TB
Retrieval pattern: unpredictable. Some old objects get sudden bursts
of reads when users search for historical documents. Access varies by
prefix with no clear rule that could be encoded in lifecycle policy.
Cost Explorer: $460/month (all Standard)

Workload context: user-uploaded shared documents (PDFs, images,
spreadsheets). Access is driven by business workflows that are
irregular. No way to predict which old objects will be accessed.
