---
description: Deploy an AWS Snowball Edge with production-grade defaults (import/export job creation, device type selection, S3 bucket configuration, device pairing and unlock, NFS interface for data transfer, Lambda functions for edge compute, cluster mode for resiliency, EKS Anywhere, shipping and return logistics, data validation reporting). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "deploy snowball edge"
  - "snowball edge"
  - "snowball"
  - "snowcone"
  - "snowball import job"
  - "snowball export job"
  - "snowball device unlock"
  - "snowball cluster mode"
  - "snowball nfs transfer"
  - "eks anywhere snowball"
  - "snowball data migration"
routes_to: snowball-edge-deployer
---

# /aws:deploy-snowball-edge

Activate the `snowball-edge-deployer` skill and deploy an AWS
Snowball Edge with production-grade defaults.

## What it does

The skill walks the deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. Job type selection (import vs export vs local compute)
2. Device type selection (Storage Optimized, Compute Optimized, Snowcone)
3. S3 bucket configuration (source or destination)
4. Device pairing and unlock (manifest + unlock code)
5. NFS interface for data transfer (start-service, mount, parallel copy)
6. Lambda functions for edge compute
7. Cluster mode (5-10 nodes for compute resiliency)
8. Shipping, tracking, and return logistics
9. Data validation and reporting
10. EKS Anywhere and long-term rental

## When to use

- You need to create a Snowball Edge import job to migrate data to S3.
- You need to create a Snowball Edge export job to download S3 data.
- You need to set up NFS for bulk data transfer on a Snowball device.
- You need cluster mode for edge compute with EKS Anywhere.
- You need to configure Lambda functions on a Snowball device.
- You need long-term Snowball Edge rental for persistent edge compute.

## When NOT to use

- **AWS DataSync** — use DataSync skills for online network data migration.
- **AWS Transfer Family (SFTP)** — different file transfer service.
- **S3 Cross-Region Replication** — for online S3-to-S3 replication.
- **Direct Connect / VPN** — for continuous network connectivity.

## How to invoke

### Slash command

```
/aws:deploy-snowball-edge
```

Then provide: job type (import/export), data volume, S3 bucket name,
shipping address ID, device type, shipping option, tags.

### Natural language

Any of these routes to the same skill:

- "create a snowball edge import job"
- "set up a snowball edge cluster for eks anywhere"
- "configure nfs transfer on my snowball device"
- "create a snowball export job"
- "deploy snowcone for edge compute"

### CLI routing

```bash
node cli/bin/cli.js route "create a snowball edge job"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Snowball
Edge jobs. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-snowball-edge

     Create a Snowball Edge import job to migrate 150 TB of data
     to S3 bucket my-migration-bucket in us-east-1. Use Edge
     Storage Optimized. Ship to addr-aaaabbbb.

Skill:
  SNOWBALL_EDGE: JID12345678 (IMPORT) — EDGE_STORAGE_OPTIMIZED
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Job type: Import (on-premises → S3)
    [✓] Device type: Edge Storage Optimized (210 TB)
    [✓] S3 bucket: my-migration-bucket (destination)
    [✓] Shipping: addr-aaaabbbb — verified
    [✓] Data transfer plan: NFS parallel copy (16 threads)
  VERIFICATION_COMMANDS:
    aws snowball describe-job --job-id <job-id> --region us-east-1
```

## References

- Skill definition: `skills/snowball-edge-deployer/SKILL.md`
- Import/export data flow: `skills/snowball-edge-deployer/references/import-export-data-flow.md`
- Cluster and compute guide: `skills/snowball-edge-deployer/references/cluster-and-compute.md`
- Eval suite: `skills/snowball-edge-deployer/evals/evals.json`
