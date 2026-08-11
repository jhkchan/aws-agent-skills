# Eval: volume-gateway-iscsi

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Volume Gateway cached mode, iSCSI target, cache and upload buffer allocated

## Prompt

Deploy a Volume Gateway in cached mode in us-east-1. Gateway name:
prod-volume-gateway. Activation key: VWXYZ-98765-QRSTU-43210-PQRSX.
Cache disk: 1 TB. Upload buffer: 500 GB. Create a cached iSCSI
volume of 1 TB. Target name: prod-volume-01. Network interface:
eni-xxxx12345. Tags: Environment=production, Storage=cached.
