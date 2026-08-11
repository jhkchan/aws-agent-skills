# Baseline (no-skill) — s3-file-gateway-nfs

> This is the response a model produces **without** the skill
> definition. It lists the activation command but misses the
> cache-vs-upload-buffer distinction (conflates them as "local disk"),
> the gateway region alignment with the S3 bucket region, the NFS
> client list restriction, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Activate the gateway and create an NFS file share:

```bash
aws storagegateway activate-gateway \
  --activation-key ABCDE-12345-FGHIJ-67890-KLMNO \
  --gateway-name prod-s3-file-gateway \
  --gateway-region us-east-1 \
  --gateway-type FILE_S3

aws storagegateway create-nfs-file-share \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --role arn:aws:iam::123456789012:role/StorageGatewayS3Role \
  --location-arn arn:aws:s3:::my-data-bucket
```

Add some local disks and you should be good.
