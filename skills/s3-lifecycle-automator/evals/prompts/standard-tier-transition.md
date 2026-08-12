# Eval prompt: standard-tier-transition

Design an automated S3 lifecycle policy for the following bucket. Emit
the standard LIFECYCLE block (POLICY, TRANSITIONS, VERSIONING,
VALIDATION, ENFORCEMENT, VERDICT, TEMPLATE).

Design reference: standard-tier-transition
Account: 111111111111
Region: us-east-1

Bucket: app-access-logs
Versioning: enabled
Requirement: transition logs from Standard to IA at 30 days, Glacier IR
at 90 days, and Deep Archive at 365 days. Expire non-current versions
after 120 days. Abort incomplete multipart uploads after 7 days.

Include the put-bucket-lifecycle-configuration CLI with all transitions
and versioning lifecycle rules.
