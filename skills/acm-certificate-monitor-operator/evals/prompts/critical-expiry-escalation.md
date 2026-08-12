# Eval: critical-expiry-escalation

**Difficulty:** hard
**Branch:** OPERATION_COMPLETED — cert 5 days from expiry, critical alarm fired, renewal status verified, DNS validation checked, CAA records checked, no conflict found

## Prompt

One of my ACM certificates (arn:aws:acm:us-east-1:123456789012:certificate/crit-001)
for api.example.com is only 5 days from expiry. The critical
alarm has fired. Check the renewal status, verify DNS validation
records are present, check CAA records for example.com, and
determine if renewal is blocked. SNS critical topic
arn:aws:sns:us-east-1:123456789012:cert-critical-escalation.
Account 123456789012, us-east-1.
