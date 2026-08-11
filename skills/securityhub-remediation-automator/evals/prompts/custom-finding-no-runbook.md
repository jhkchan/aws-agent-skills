# Eval prompt: custom-finding-no-runbook

Design an automated Security Hub remediation workflow for the following
finding. Emit the standard REMEDIATION block (FINDING_TYPE, STANDARD,
SEVERITY_ROUTE, RUNBOOK, TRIGGER, SAFETY, SUPPRESSION, VERDICT, GAP,
TEMPLATE).

Design reference: custom-finding-no-runbook
Account: 111111111111
Region: us-east-1

Standard: Custom
Finding type: Custom/ExposedCredentialsInLambdaEnv
Severity: HIGH
Sample finding resource: arn:aws:lambda:us-east-1:111111111111:function:api-handler

No managed SSM runbook maps to this finding type. The remediation
requires reading the Lambda environment variables, rotating the exposed
credential via Secrets Manager, and updating the function configuration.
Pre-prod validation: NOT completed (no custom Lambda fixer built yet).
