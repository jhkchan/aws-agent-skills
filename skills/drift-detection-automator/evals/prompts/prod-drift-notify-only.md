# Eval prompt: prod-drift-notify-only

Design an automated CloudFormation drift detection workflow for the
following production stack. Emit the standard DRIFT_AUTOMATION block.

Design reference: prod-drift-notify-only
Account: 111111111111
Region: us-east-1

Stack: prod-payment-service (CloudFormation, 42 resources)
Environment: production (critical)
Detection cadence: daily (02:00 UTC)
SNS topic: arn:aws:sns:us-east-1:111111111111:drift-alerts-critical
3 resources drifted: SecurityGroups (modified), IAM policy (changed),
  ALB listener rule (modified)
