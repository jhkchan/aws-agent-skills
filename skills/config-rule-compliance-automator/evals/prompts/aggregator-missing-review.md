# Eval prompt: aggregator-missing-review

Design a multi-account Config compliance setup and identify any gaps.
Emit the standard COMPLIANCE block (RULES, REMEDIATION, AGGREGATOR,
FRAMEWORK_DEPLOYMENT, VERDICT, TEMPLATE).

Design reference: aggregator-missing-review
Account: 111111111111
Region: us-east-1 (single region only)

Framework: CIS AWS Foundations Benchmark.
Existing rules: root-account-mfa-enabled, cloudtrail-enabled (managed).
Config Aggregator: NOT CONFIGURED.
StackSet auto-deployment: DISABLED.
Regions covered: us-east-1 only.
Config recorder: active.
