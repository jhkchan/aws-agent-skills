# Eval: mgmt-eds-with-data-protection

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — management EDS, 90-day retention, EmailAddress + PhoneNumber masking, CloudWatch query failure alarm

## Prompt

Create a CloudTrail Lake event data store for management events.
EDS name: mgmt-events-eds. Retention: 90 days. I need data
protection to mask EmailAddress and PhoneNumber. CloudWatch alarm
for query failures to SNS
arn:aws:sns:us-east-1:123456789012:ct-lake-alerts. Account:
123456789012. Region us-east-1. Tags: Environment=production,
Domain=security.
