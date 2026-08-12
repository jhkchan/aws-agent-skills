# Eval prompt: cryptocurrency-ec2-auto-isolate

Design an automated GuardDuty response workflow for the following finding.
Emit the standard AUTOMATION block. Include snapshot for forensics and
immediate IAM key revocation (Critical severity — no last-used check).

Design reference: cryptocurrency-ec2-auto-isolate
Account: 111111111111
Region: us-east-1

GuardDuty finding type: CryptoCurrency:EC2/BitcoinTool
Severity: 9.0 (CRITICAL)
Sample resource: i-0compromised789
Isolation SG: sg-isolation-forensics
SNS topic: arn:aws:sns:us-east-1:111111111111:guardduty-alerts
Lambda: guardduty-auto-remediation
Malware Protection: enabled
Pre-prod validation: completed.
