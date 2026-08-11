# Eval prompt: versioning-bloat

Optimise the following S3 bucket for storage cost. Walk the storage-class
analysis framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

BucketName: bucket-versioning-bloat
Region: us-east-1
Storage (total): 50 TB
Current version storage: 38 TB
Noncurrent version storage: 12 TB (24% of total)
Delete markers: 450,000
Storage class distribution:
  - Standard: 35 TB (current) + 10 TB (noncurrent)
  - Standard-IA: 3 TB (current) + 2 TB (noncurrent)
Versioning: Enabled
Lifecycle policy: none (no current or noncurrent rules)
Intelligent-Tiering: not configured
IncompleteMultipartUploads: 2 TB
Storage Lens: noncurrent versions growing 8% per month
Retrieval pattern: only current versions accessed

Workload context: application-managed document store. Application
overwrites documents frequently (average 3 versions per object).
Versioning was enabled for data protection but no lifecycle rules
were ever deployed. Only current versions are ever read.
