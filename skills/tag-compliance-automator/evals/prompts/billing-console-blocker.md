# Eval prompt: billing-console-blocker

Audit the following tag compliance setup and identify the gap blocking
cost allocation tag activation. Emit the standard COMPLIANCE block.

Design reference: billing-console-blocker
Organization ID: o-xxxxxxx
Root ID: r-xxxx
Account: 111111111111 (payer)
Region: us-east-1

Required tags: Environment, Owner, CostCenter.
TagPolicy: deployed and enforced on EC2 and S3.
Config rules: required-tags-core deployed and evaluating.
Auto-tagger: deployed with EC2->EBS/ENI propagation.
Cost allocation tags: BLOCKED — ce update-cost-allocation-tags-status
returns AccessDeniedException.
Billing console IAM access: NOT enabled.
