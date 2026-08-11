# Baseline (no-skill) response: deploy-sftp-directory-service-ready

This file captures what a generic assistant produces WITHOUT the
transfer-family-deployer skill loaded.

---

To create an SFTP server federated with AWS Directory Service:

```bash
aws transfer create-server \
  --description prod-sftp-ad \
  --protocols SFTP \
  --endpoint-type VPC_ENDPOINT \
  --identity-provider-type AWS_DIRECTORY_SERVICE \
  --identity-provider-details DirectoryId=d-abc123 \
  --vpc-id vpc-abc123 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-ssh
```

Users sign in with their AD credentials (DOMAIN\username + password).
