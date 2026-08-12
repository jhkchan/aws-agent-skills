# Eval prompt: staging-daily-drift-auto-remediate

Design an automated CloudFormation drift detection workflow for the
following stack. Emit the standard DRIFT_AUTOMATION block (DETECTION,
COMPARISON, NOTIFICATION, REMEDIATION, INTEGRATION, SAFETY, AUDIT,
VERDICT, TEMPLATE).

Design reference: staging-daily-drift-auto-remediate
Account: 111111111111
Region: us-east-1

Stack: staging-web-app (CloudFormation, 15 resources)
Environment: staging (non-production)
Detection cadence: daily (02:00 UTC)
SNS topic: arn:aws:sns:us-east-1:111111111111:drift-alerts
SSM Automation: Custom-DriftRemediation (tested in sandbox)
Suppression rules needed: ASG DesiredCapacity, Lambda RoutingConfig
Config Aggregator: enabled
Pre-prod validation: completed (3 deliberate drift tests, all remediated).
