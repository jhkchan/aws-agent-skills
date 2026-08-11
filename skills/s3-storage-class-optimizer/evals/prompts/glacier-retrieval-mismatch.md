# Eval prompt: glacier-retrieval-mismatch

Optimise the following S3 bucket for storage cost. Walk the storage-class
analysis framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

BucketName: bucket-glacier-retrieval-mismatch
Region: us-east-1
Storage (total): 30 TB
Storage class distribution:
  - Standard: 5 TB (17%)
  - Standard-IA: 7 TB (23%)
  - Glacier Deep Archive: 18 TB (60%)
Versioning: Suspended
Lifecycle policy: Enabled (Standard→IA 30d, →DA 90d)
Intelligent-Tiering: not configured
Storage Lens:
  - Objects aged 0-30 days: 5 TB
  - Objects aged 31-90 days: 7 TB
  - Objects aged >90 days: 18 TB
Retrieval pattern: 15% of archived data retrieved per month
(approximately 2.7 TB/month retrieved from Deep Archive using
standard retrieval at $0.02/GB)
Cost Explorer: $54/month storage + $55.30/month retrieval = $109.30 total

Workload context: compliance archive where business analysts run
quarterly audits that access a significant portion of the archived
data. The lifecycle policy was too aggressive (pushing to Deep Archive
at 90 days) and the retrieval cost is now exceeding the storage savings.
