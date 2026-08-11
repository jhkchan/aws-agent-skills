# Baseline (no-skill) response: deploy-ftp-public-endpoint-blocked

This file captures what a generic assistant produces WITHOUT the
transfer-family-deployer skill loaded.

---

To create your FTP server:

```bash
aws transfer create-server \
  --description legacy-ftp-public \
  --protocols FTP \
  --endpoint-type PUBLIC \
  --identity-provider-type SERVICE_MANAGED \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole
```

FTP is convenient for legacy clients that do not support SFTP or FTPS.
