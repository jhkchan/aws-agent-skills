# Eval prompt: tag-policy-org-baseline

Design an Organizations TagPolicy baseline enforcing required tags
across production resources. Emit the standard GOVERNANCE block
(SCOPE, STRATEGY, POLICY, AUTOMATION, COMPLIANCE, VERDICT, GAP,
TEMPLATE).

Design reference: tag-policy-org-baseline
Organization ID: o-xxxxxxx
Root ID: r-xxxx
Region: us-east-1

Required tags: Environment, Owner, Project, CostCenter.
Environment allowed_values: dev, staging, prod.
CostCenter allowed_values: cc-1001, cc-1002, cc-1003, cc-9999.
Target resource types for enforced_for: EC2 instances, S3 buckets,
Lambda functions, RDS DB instances.

Tag policies are NOT currently enabled at the org root.
