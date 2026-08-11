# Baseline (no-skill) response: deploy-sftp-missing-iam-role

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
  --home-directory /prod-sftp-inbox/alice
```

Make sure the IAM role exists before adding users.
