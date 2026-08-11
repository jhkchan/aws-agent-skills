# Baseline (no-skill) — smb-active-directory

> This is the response a model produces **without** the skill
> definition. It creates an SMB share but misses the AD join step
> entirely, uses guest access instead of ActiveDirectory
> authentication, does not configure audit logging, and omits the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create the SMB file share:

```bash
aws storagegateway activate-gateway \
  --activation-key ABCDE-11111-FGHIJ-22222-KLMNO \
  --gateway-name prod-smb-gateway \
  --gateway-type FILE_S3

aws storagegateway create-smb-file-share \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --role arn:aws:iam::123456789012:role/StorageGatewayS3Role \
  --location-arn arn:aws:s3:::smb-share-bucket \
  --guest-password "GuestPass123!"
```

This will create a guest-access SMB share.
