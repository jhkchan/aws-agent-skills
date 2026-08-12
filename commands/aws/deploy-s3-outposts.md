---
description: Provision Amazon S3 on Outposts with production-grade defaults (VPC endpoint for access, outpost bucket, access points, STANDARD-only storage, SSE-S3 encryption, one-way replication to cloud, object lock, capacity monitoring). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "s3 outposts"
  - "s3 on outpost"
  - "outpost bucket"
  - "s3 outpost endpoint"
  - "s3 outpost access point"
  - "s3 outpost replication"
  - "object lock outpost"
  - "s3 outpost capacity"
  - "s3 outpost encryption"
  - "outpost s3 bucket"
routes_to: s3-outposts-deployer
---

# /aws:deploy-s3-outposts

Activate the `s3-outposts-deployer` skill and provision Amazon S3 on
Outposts with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. S3 on Outposts vs cloud S3 (key differences)
2. Endpoint (mandatory VPC endpoint for access)
3. Bucket creation (s3control API)
4. Access points (regional vs outpost)
5. Storage class (STANDARD only)
6. Encryption (SSE-S3 only, no KMS)
7. Versioning and lifecycle (expiration only, no cloud tiers)
8. Replication (one-way Outpost to cloud)
9. Object lock (WORM, at creation only)
10. Capacity management and CloudWatch monitoring

## When to use

- You need to create an S3 bucket on an Outpost.
- You need a VPC endpoint for accessing Outpost S3.
- You need replication from Outpost to cloud S3 for DR.
- You need object lock (WORM) on an Outpost bucket.
- You need capacity monitoring for finite Outpost storage.

## When NOT to use

- **Standard cloud S3** — use regular S3 skills.
- **FSx on Outposts** — use FSx skills for file storage.
- **EBS on Outposts** — use EBS skills for block storage.
- **Outpost rack provisioning** — use Outposts management skills.

## How to invoke

### Slash command

```
/aws:deploy-s3-outposts
```

Then provide: Outpost ID, bucket name, endpoint subnet/SG details,
access point config, replication destination, object lock decision,
capacity alarm threshold, tags.

### Natural language

Any of these routes to the same skill:

- "create an s3 bucket on my outpost"
- "set up s3 on outposts with endpoint"
- "replicate outpost s3 to cloud"
- "configure object lock on outpost bucket"
- "monitor outpost s3 capacity"

### CLI routing

```bash
node cli/bin/cli.js route "create s3 outposts bucket"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create S3 on
Outposts infrastructure. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-s3-outposts

     Create an S3 bucket on Outpost op-0abc123def456. Endpoint
     in subnet subnet-abc123. Replicate to s3://cloud-dr-bucket.
     Versioning enabled.

Skill:
  S3_OUTPOST: my-outpost-bucket on op-0abc123def456
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Endpoint: Available (subnet subnet-abc123)
    [✓] Bucket: my-outpost-bucket
    [✓] Storage class: STANDARD
    [✓] Encryption: SSE-S3
    [✓] Replication: Outpost → cloud (s3://cloud-dr-bucket)
  VERIFICATION_COMMANDS:
    aws s3control list-regional-buckets --account-id <account-id>
    aws s3outposts list-endpoints
```

## References

- Skill definition: `skills/s3-outposts-deployer/SKILL.md`
- Endpoints guide: `skills/s3-outposts-deployer/references/endpoints-and-networking.md`
- Replication guide: `skills/s3-outposts-deployer/references/replication-and-capacity.md`
- Eval suite: `skills/s3-outposts-deployer/evals/evals.json`
