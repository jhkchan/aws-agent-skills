# Eval prompt: finding-suppression-accepted-risk

Design an Inspector v2 automation workflow for the following
finding on a legacy EC2 instance that has no patch available.
Emit the standard FINDING block (SEVERITY, DETECTION, RESPONSE,
SSM_RUNBOOK, VERIFICATION, MULTI_ACCOUNT, VERDICT, TEMPLATE).
Make the suppression rationale explicit (decommission approved,
isolated VPC, no patch available).

Design reference: finding-suppression-accepted-risk
Account: 111111111111
Region: us-east-1

Finding: CVE-2026-7777 on openssl 1.0.1 (no vendor patch, CVSS 9.0)
Severity: CRITICAL
Resource: AWS_EC2_INSTANCE i-legacy000123 (legacy-billing-app)
Instance is in isolated VPC, no internet egress.
Decommission scheduled: 2027-Q1 (approved by CISO).
Finding ARN: arn:aws:inspector2:us-east-1:111111111111:finding/suppressed001
