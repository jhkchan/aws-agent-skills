# Eval prompt: already-optimal-bucket

Optimise the following S3 bucket for storage cost. Walk the storage-class
analysis framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

BucketName: bucket-already-optimal-bucket
Region: us-east-1
Storage (total): 10 TB
Storage class distribution:
  - Standard: 3 TB (30%)
  - Standard-IA: 2 TB (20%)
  - Glacier Instant Retrieval: 2 TB (20%)
  - Glacier Deep Archive: 3 TB (30%)
Versioning: Suspended
Lifecycle policy: Enabled (Standard→IA 30d, →GIR 90d, →DA 180d)
Intelligent-Tiering: Enabled on /user-uploads/ prefix
Storage Lens: all objects align with lifecycle transitions
Retrieval pattern: <1% retrieval of archived objects
Cost Explorer: $115/month — matches expected class distribution

Workload context: well-managed analytics bucket. Lifecycle policy was
deployed 6 months ago and Storage Lens confirms objects are transitioning
correctly. Intelligent-Tiering was added for the user-uploads prefix
which has unpredictable access. No versioning bloat.
