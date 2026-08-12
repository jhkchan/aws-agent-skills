# Eval prompt: standard-90-day-rotation

Design an IAM access key rotation pipeline for the following key. Emit
the standard ROTATION block (USER, KEY, CLASSIFICATION, DETECTION,
ROTATION_FLOW, OVERLAP, NOTIFICATION, EXCEPTIONS, AUDIT, VERDICT,
TEMPLATE).

Design reference: standard-90-day-rotation
Account: 111111111111
Region: us-east-1

IAM user: deployment-user
Access key: AKIAXYZ123 (Active)
Created: 91 days ago
Last used: 2 hours ago (S3, CloudFormation per access advisor)
Key slots used: 1 of 2 (one slot free)
Exception list: user not on break-glass list
SNS topic: arn:aws:sns:us-east-1:111111111111:key-rotation-alerts
