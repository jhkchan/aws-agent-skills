# Eval prompt: case-sensitivity-mismatch

Diagnose why the following tag compliance setup reports NON_COMPLIANT
on resources that appear to be tagged. Emit the standard COMPLIANCE
block with the root cause in the GAP field.

Design reference: case-sensitivity-mismatch
Organization ID: o-xxxxxxx
Root ID: r-xxxx
Account: 111111111111
Region: us-east-1

Required tags: Environment, Owner.
TagPolicy: TagKey Environment, case_sensitive: true,
enforced_for AWS::EC2::Instance.
Config rule: required-tags-core, InputParameters tag1Key=Environment.
Auto-tagger Lambda: stamps key "environment" (lowercase) from the
EventBridge event detail.
Observed: instances are TagPolicy-NON_COMPLIANT AND Config-NON_COMPLIANT
despite the Lambda firing successfully on every RunInstances event.
