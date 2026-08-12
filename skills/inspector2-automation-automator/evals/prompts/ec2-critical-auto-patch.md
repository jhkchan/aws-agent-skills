# Eval prompt: ec2-critical-auto-patch

Design an Inspector v2 automation workflow for the following
finding. Emit the standard FINDING block (SEVERITY, DETECTION,
RESPONSE, SSM_RUNBOOK, VERIFICATION, MULTI_ACCOUNT, VERDICT,
TEMPLATE).

Design reference: ec2-critical-auto-patch
Account: 111111111111
Region: us-east-1

Finding: CVE-2026-1234 on openssl (CVSS 9.8)
Severity: CRITICAL
Resource: AWS_EC2_INSTANCE i-0abc123def456 (Amazon Linux 2,
  SSM agent healthy, Patch Group tag = "critical-patch-group")
Inspector coverage: enabled (EC2/ECR/Lambda)
SSM service role ARN:
  arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole
Pre-prod validation: completed (Cycle 1 Scan + Cycle 2 Install
  in non-prod; ready for prod).
