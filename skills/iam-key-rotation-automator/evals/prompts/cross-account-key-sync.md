# Eval prompt: cross-account-key-sync

Design an IAM access key rotation pipeline for the following cross-
account key. Include the cross-account sync flow. Emit the standard
ROTATION block (USER, KEY, CLASSIFICATION, DETECTION, ROTATION_FLOW,
OVERLAP, NOTIFICATION, EXCEPTIONS, AUDIT, VERDICT, TEMPLATE).

Design reference: cross-account-key-sync
Account A (issuer): 111111111111
Account B (consumer): 222222222222
Region: us-east-1

IAM user (in Account A): cross-account-svc
Access key: AKIACROSS111 (Active, in Account A)
Created: 92 days ago
Last used: 5 hours ago
Key slots: 1 of 2 used
Consumer: Application in Account B reads key from Secrets Manager
Cross-account role in Account B: arn:aws:iam::222222222222:role/key-sync-target
SNS topic: arn:aws:sns:us-east-1:111111111111:key-rotation-alerts
