# Baseline (no-skill) response: deploy-sftp-service-managed-ready

This file captures what a generic assistant produces WITHOUT the
transfer-family-deployer skill loaded.

---

To create your SFTP server:

```bash
aws transfer create-server \
  --description prod-sftp-inbox \
  --protocols SFTP \
  --endpoint-type PUBLIC \
  --identity-provider-type SERVICE_MANAGED \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole

aws transfer create-user \
  --server-id s-abc123 \
  --user-name alice \
  --role arn:aws:iam::111111111111:role/TransferUserS3Role \
  --home-directory /prod-sftp-inbox/alice \
  --ssh-public-key-body "ssh-rsa AAAAB3..."
```

Repeat for each user. Make sure the IAM role can access the S3 bucket.
