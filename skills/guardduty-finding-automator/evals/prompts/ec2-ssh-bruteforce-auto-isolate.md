# Eval prompt: ec2-ssh-bruteforce-auto-isolate

Design an automated GuardDuty response workflow for the following finding.
Emit the standard AUTOMATION block (FINDING_TYPE, SEVERITY, ROUTING,
REMEDIATION, NOTIFICATION, INTEGRATION, SAFETY, AUDIT, VERDICT, TEMPLATE).

Design reference: ec2-ssh-bruteforce-auto-isolate
Account: 111111111111
Region: us-east-1

GuardDuty finding type: UnauthorizedAccess:EC2/SSHBruteForce
Severity: 7.5 (HIGH)
Sample resource: i-0abc123def456 (production web server)
Isolation SG exists: sg-isolation-forensics
SNS topic: arn:aws:sns:us-east-1:111111111111:guardduty-alerts
Lambda remediation function: guardduty-auto-remediation
Pre-prod validation: completed (3 test findings, all isolated correctly).
