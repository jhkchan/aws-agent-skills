# Eval prompt: break-glass-exception

Design an IAM access key rotation pipeline for the following key. Emit
the standard ROTATION block (USER, KEY, CLASSIFICATION, DETECTION,
ROTATION_FLOW, OVERLAP, NOTIFICATION, EXCEPTIONS, AUDIT, VERDICT, GAP,
TEMPLATE).

Design reference: break-glass-exception
Account: 111111111111
Region: us-east-1

IAM user: break-glass-admin
Access key: AKIABREAK789 (Active)
Created: 365 days ago
Last used: 45 days ago (during a Sev-1 incident, accessed STS + IAM)
Exception list: user IS on break-glass list (reason: Emergency access,
owner: security-team)
SNS topic: arn:aws:sns:us-east-1:111111111111:key-rotation-alerts

The operator wants this key auto-rotated immediately.
