# Eval prompt: unsupported-crr-requested-missing

Design a deployment plan for an S3 Express One Zone directory bucket.
Emit the standard VERDICT block (DIRECTORY_BUCKET_SPEC, VERDICT,
CHECKLIST, VERIFICATION_COMMANDS).

Requirements:

- Base bucket name: production-data
- AZ: us-east-1a
- Region: us-east-1
- Cross-region replication to eu-west-1 for disaster recovery
- Versioning enabled for rollback capability
- Object Lock for compliance retention (7-year hold)
- Compute: 4 x c7n.large in use1-az1

Additional context: the compliance team requires cross-region
replication, versioning, and Object Lock for all production data stores.
The operator wants to use S3 Express One Zone for its latency
characteristics but must meet these compliance requirements. The
workload is a production data store, not a cache.
