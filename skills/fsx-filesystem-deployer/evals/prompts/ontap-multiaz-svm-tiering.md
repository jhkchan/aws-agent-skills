# Eval: ontap-multiaz-svm-tiering

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — ONTAP Multi-AZ, SVM created, volume with auto-tiering and storage efficiency enabled

## Prompt

Create an FSx for ONTAP file system in us-east-1. Multi-AZ
deployment, 1024 GB storage. VPC vpc-eee55566, subnets
subnet-eee555 (us-east-1a) and subnet-fff666 (us-east-1b).
Create SVM svm-prod and volume vol-prod (1 TB) with auto tiering
policy and storage efficiency enabled. Tags: Environment=production,
ManagedBy=cloudops.
