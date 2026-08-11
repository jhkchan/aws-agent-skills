# Eval prompt: six-key-custom-rule

Design a tag compliance automation baseline that enforces 6 required tag
keys. The managed required-tags rule checks only 5. Emit the standard
COMPLIANCE block including the Config rule configuration for all 6 keys.

Design reference: six-key-custom-rule
Organization ID: o-xxxxxxx
Root ID: r-xxxx
Account: 111111111111
Region: us-east-1

Required tags: Environment, Owner, CostCenter, Project, Application,
ComplianceTier.
Target resource types: EC2 instances, S3 buckets, Lambda functions.
Auto-tagger: deployed with EC2->EBS/ENI propagation.
Cost allocation tags: active for all 6 keys.
Pre-prod validation: completed.
