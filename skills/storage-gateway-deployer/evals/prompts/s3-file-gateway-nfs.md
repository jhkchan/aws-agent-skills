# Eval: s3-file-gateway-nfs

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — S3 File Gateway, NFS file share, cache and upload buffer sized independently, gateway region matches S3 bucket region

## Prompt

Deploy an S3 File Gateway in us-east-1. Gateway name:
prod-s3-file-gateway. Activation key: ABCDE-12345-FGHIJ-67890-KLMNO.
S3 bucket: my-data-bucket (us-east-1). IAM role:
arn:aws:iam::123456789012:role/StorageGatewayS3Role. Cache disk:
500 GB. Upload buffer disk: 300 GB. Create an NFS file share with
client list 10.0.0.0/16. Default storage class S3_STANDARD. Tags:
Environment=production.
