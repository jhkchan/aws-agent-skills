# Eval prompt: multi-account-stackset-drift

Design a multi-account CloudFormation drift detection pipeline using
StackSets and Config Aggregator. Emit the standard DRIFT_AUTOMATION
block. Include the StackSet deployment pattern and per-instance drift
detection iteration.

Design reference: multi-account-stackset-drift
Delegated admin: 111111111111
Target OU: ou-abc1-1234abcd (20 member accounts)
Regions: us-east-1, us-west-2, eu-west-1
StackSet: drift-detection-pipeline (Lambda + EventBridge rule)
Stack instances: ~60 (20 accounts x 3 regions)
Config Aggregator: drift-visibility-aggregator
Auto-deployment: enabled for new accounts
SNS topic (centralized): arn:aws:sns:us-east-1:111111111111:drift-alerts
