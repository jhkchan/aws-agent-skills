# Eval prompt: min-days-validation-fail

Design a lifecycle policy for the following bucket. Emit the standard
LIFECYCLE block (POLICY, TRANSITIONS, VERSIONING, VALIDATION,
ENFORCEMENT, VERDICT, GAP, TEMPLATE).

Design reference: min-days-validation-fail
Account: 111111111111
Region: us-east-1

Bucket: cost-optimization-target
Versioning: disabled
Requirement: transition from Standard to IA at 15 days, Standard-IA to
Glacier IR at 60 days.
NoncurrentVersionExpiration: NOT configured.

The operator says "we want the fastest possible transition to cheap
storage."
