# Eval prompt: overlap-window-rotation

Design an IAM access key rotation pipeline for the following key.
Include a detailed overlap window design. Emit the standard ROTATION
block (USER, KEY, CLASSIFICATION, DETECTION, ROTATION_FLOW, OVERLAP,
NOTIFICATION, EXCEPTIONS, AUDIT, VERDICT, TEMPLATE).

Design reference: overlap-window-rotation
Account: 111111111111
Region: us-east-1

IAM user: ci-cd-pipeline-user
Access key: AKIACICD456 (Active)
Created: 95 days ago
Last used: 3 days ago (CodeBuild, ECR, S3 per access advisor)
Key slots used: 1 of 2
Exception list: not on exception list
Application: CI/CD pipeline on CodeBuild (reads key from Secrets Manager)
SNS topic: arn:aws:sns:us-east-1:111111111111:key-rotation-alerts
