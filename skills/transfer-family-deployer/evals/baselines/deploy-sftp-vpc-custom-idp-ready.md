# Baseline (no-skill) response: deploy-sftp-vpc-custom-idp-ready

This file captures what a generic assistant produces WITHOUT the
transfer-family-deployer skill loaded.

---

To create a VPC SFTP/FTPS server with a custom IdP:

```bash
aws transfer create-server \
  --description prod-sftp-vpc-custom-idp \
  --protocols SFTP FTPS \
  --endpoint-type VPC_ENDPOINT \
  --identity-provider-type API_GATEWAY \
  --identity-provider-details Url=https://abc123.execute-api.us-east-1.amazonaws.com/prod/,InvocationRole=arn:aws:iam::111111111111:role/TransferIdPInvocationRole \
  --certificate arn:aws:acm:us-east-1:111111111111:certificate/abc-123 \
  --vpc-id vpc-abc123 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-ssh sg-ftps
```

Make sure your API Gateway Lambda returns the right fields.
