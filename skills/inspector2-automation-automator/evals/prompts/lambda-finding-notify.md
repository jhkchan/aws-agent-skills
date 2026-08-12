# Eval prompt: lambda-finding-notify

Design an Inspector v2 automation workflow for the following
Lambda code scan finding. Emit the standard FINDING block
(SEVERITY, DETECTION, RESPONSE, SSM_RUNBOOK, VERIFICATION,
MULTI_ACCOUNT, VERDICT, TEMPLATE). Make clear that Lambda code
scan findings require function code update via CI/CD, not SSM
patching.

Design reference: lambda-finding-notify
Account: 111111111111
Region: us-east-1

Finding: CVE-2026-9090 on lodash dependency (CVSS 7.5)
Severity: HIGH
Resource: AWS_LAMBDA_FUNCTION order-processor-prod
SNS topic ARN: arn:aws:sns:us-east-1:111111111111:app-team-notify
Lambda function is deployed via CodePipeline (CI/CD available).
No runtime issues reported (GuardDuty clean).
