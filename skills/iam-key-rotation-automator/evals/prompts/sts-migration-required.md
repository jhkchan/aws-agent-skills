# Eval prompt: sts-migration-required

Design an IAM access key rotation pipeline for the following key. Emit
the standard ROTATION block (USER, KEY, CLASSIFICATION, DETECTION,
ROTATION_FLOW, OVERLAP, NOTIFICATION, EXCEPTIONS, AUDIT, VERDICT, GAP,
TEMPLATE).

Design reference: sts-migration-required
Account: 111111111111
Region: us-east-1

IAM user: ec2-app-svc-user
Access key: AKIAEC2APP222 (Active)
Created: 120 days ago
Last used: 1 hour ago (S3, DynamoDB per access advisor)
Key slots: 1 of 2 used
Consumer: EC2 instance i-0abc123def running a Python app
The app reads the access key from environment variables.
The EC2 instance currently has no IAM instance profile attached.
SNS topic: arn:aws:sns:us-east-1:111111111111:key-rotation-alerts

The operator wants to rotate the key.
