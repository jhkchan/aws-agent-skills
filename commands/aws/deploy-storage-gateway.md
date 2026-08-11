---
description: Deploy an AWS Storage Gateway with production-grade defaults (S3 File Gateway, FSx File Gateway, Volume Gateway cached/stored, Tape Gateway VTL, cache vs upload buffer sizing, NFS/SMB file shares, SMB Active Directory, iSCSI volumes, VTL tapes, bandwidth rate limits, CloudWatch monitoring, audit logging). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "deploy storage gateway"
  - "storage gateway"
  - "s3 file gateway"
  - "volume gateway"
  - "tape gateway"
  - "fsx file gateway"
  - "storage gateway activation"
  - "cache upload buffer"
  - "nfs file share"
  - "smb file share"
  - "iscsi target"
  - "vtl tape"
  - "bandwidth rate limit"
  - "smb active directory"
routes_to: storage-gateway-deployer
---

# /aws:deploy-storage-gateway

Activate the `storage-gateway-deployer` skill and deploy an AWS
Storage Gateway with production-grade defaults.

## What it does

The skill walks the deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. Gateway type selection (S3 File, FSx File, Volume, Tape)
2. Gateway activation (activation key)
3. Local disk allocation (cache vs upload buffer)
4. S3 File Gateway NFS/SMB file shares
5. SMB Active Directory integration
6. Volume Gateway iSCSI targets
7. Tape Gateway VTL
8. Bandwidth rate limits
9. CloudWatch monitoring and audit logging
10. Recent features

## When to use

- You need to deploy an S3 File Gateway with NFS or SMB file shares.
- You need a Volume Gateway (cached or stored) with iSCSI volumes.
- You need a Tape Gateway VTL for backup software.
- You need SMB file shares joined to Active Directory.
- You need bandwidth rate limit scheduling.
- You need CloudWatch monitoring for cache hit ratio and buffer usage.

## When NOT to use

- **AWS DataSync** — use DataSync skills for online data migration.
- **AWS Transfer Family (SFTP)** — different file transfer service.
- **Storage Gateway troubleshooting** — use a troubleshooter skill.
- **Pure S3 access from cloud** — no gateway needed for cloud-native apps.

## How to invoke

### Slash command

```
/aws:deploy-storage-gateway
```

Then provide: gateway type, activation key, gateway name, region,
S3 bucket name (for file gateways), cache disk size, upload buffer
disk size, file share type (NFS/SMB), AD domain details (if SMB),
tags.

### Natural language

Any of these routes to the same skill:

- "deploy an s3 file gateway with nfs"
- "set up a volume gateway in cached mode"
- "deploy a tape gateway for backup"
- "create an smb file share with active directory"
- "configure storage gateway bandwidth limits"

### CLI routing

```bash
node cli/bin/cli.js route "deploy a storage gateway"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to deploy Storage
Gateway. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-storage-gateway

     Deploy an S3 File Gateway in us-east-1. Gateway name:
     prod-s3-file-gateway. Activation key: ABCDE-12345-FGHIJ-67890-KLMNO.
     S3 bucket: my-data-bucket. Cache: 500 GB. Upload buffer: 300 GB.
     NFS clients: 10.0.0.0/16.

Skill:
  STORAGE_GATEWAY: prod-s3-file-gateway (FILE_S3) — sgw-AAAAA
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Gateway type: S3 File Gateway
    [✓] Cache: 500 GB — allocated
    [✓] Upload buffer: 300 GB — allocated
    [✓] File share (NFS): share → s3://my-data-bucket
    [✓] Region: us-east-1 (matches S3 bucket)
  VERIFICATION_COMMANDS:
    aws storagegateway describe-gateway-information --gateway-arn <arn> --region us-east-1
    aws storagegateway list-file-shares --gateway-arn <arn> --region us-east-1
```

## References

- Skill definition: `skills/storage-gateway-deployer/SKILL.md`
- Cache and buffer guide: `skills/storage-gateway-deployer/references/cache-and-buffer-sizing.md`
- File share and SMB guide: `skills/storage-gateway-deployer/references/file-share-and-smb.md`
- Eval suite: `skills/storage-gateway-deployer/evals/evals.json`
