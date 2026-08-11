# Eval prompt: custom-lambda-remediation

Design a Config compliance automation for CIS 2.1 (default SG no
ingress) requiring a custom Lambda rule. Emit the standard COMPLIANCE
block (RULES, REMEDIATION, AGGREGATOR, FRAMEWORK_DEPLOYMENT, VERDICT,
TEMPLATE).

Design reference: custom-lambda-remediation
Account: 111111111111
Region: us-east-1

Config recorder: active, includes AWS::EC2::SecurityGroup.
Framework: CIS 2.1 — default security group must have no ingress rules.
No managed rule covers this — custom Lambda rule required.
Remediation: Custom SSM document (revoke default SG ingress).
Trigger: Manual (destructive — false positive risk on production SGs).
Pre-prod validation: completed (3 SGs tested).
