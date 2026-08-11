# Eval prompt: conformance-pack-cis-stacksets

Design a full CIS conformance pack deployment via CloudFormation
StackSets. Emit the standard COMPLIANCE block (RULES, REMEDIATION,
AGGREGATOR, FRAMEWORK_DEPLOYMENT, VERDICT, TEMPLATE).

Design reference: conformance-pack-cis-stacksets
Organization management account: 111111111111
Target OU: ou-xxxx-security (all member accounts)
Regions: us-east-1, us-west-2, eu-west-1, ap-southeast-2

Framework: CIS AWS Foundations Benchmark (controls 1.x, 2.x, 3.x, 4.x).
Deployment method: CloudFormation StackSets.
Permission model: SERVICE_MANAGED.
Auto-deployment: required for new accounts.
Config recorder: active in all member accounts.
Organizations integration: enabled (AWSServiceRoleForConfig present).

Include the StackSet deployment CLI with CAPABILITY_IAM.
