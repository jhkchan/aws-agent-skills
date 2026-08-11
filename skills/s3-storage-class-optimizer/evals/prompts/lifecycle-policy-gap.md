# Eval prompt: lifecycle-policy-gap

Optimise the following S3 bucket for storage cost. Walk the storage-class
analysis framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

BucketName: bucket-lifecycle-policy-gap
Region: us-east-1
Storage (total): 45 TB
Storage class distribution:
  - Standard: 32 TB (71%)
  - Standard-IA: 8 TB (18%)
  - Glacier Instant Retrieval: 0 TB
  - Glacier Flexible Retrieval: 3 TB (7%)
  - Glacier Deep Archive: 2 TB (4%)
Versioning: Enabled
Lifecycle policy: none
Intelligent-Tiering: not configured
Storage Lens (last 30 days):
  - Objects aged 0-30 days: 12 TB
  - Objects aged 31-90 days: 9 TB
  - Objects aged 91-180 days: 6 TB
  - Objects aged 181-365 days: 5 TB
  - Objects aged >365 days: 13 TB
Retrieval frequency: <1% of objects accessed after 90 days
Cost Explorer (last 30 days): $1,035/month on S3 (71% Standard rate)

Workload context: data lake with raw ingestion. Objects are write-once-
read-rarely. No compliance retention requirements beyond 7 years for
the raw tier. Predictable access pattern (new data written daily,
historical data almost never accessed).
