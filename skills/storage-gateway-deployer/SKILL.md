---
name: storage-gateway-deployer
description: 'Deploys AWS Storage Gateway with production defaults: gateway types (S3 File Gateway, FSx File Gateway, Volume Gateway cached/stored, Tape Gateway), gateway activation via activation key, local disk allocation (cache vs upload buffer), S3 File Gateway NFS/SMB file share exports, file share configuration (S3 bucket mapping, default storage class), SMB Active Directory integration, Volume Gateway iSCSI targets, Tape Gateway VTL with backup software, CloudWatch monitoring, bandwidth rate limit scheduling, automatic file share refresh, SMB guest password, and audit logging. Emits a READY_TO_DEPLOY checklist with verification commands. Use when deploying Storage Gateway, setting up S3 File Gateway, configuring Volume Gateway iSCSI, deploying Tape Gateway VTL, or configuring SMB Active Directory. Triggers: deploy storage gateway, s3 file gateway, volume gateway, tape gateway, fsx file gateway, storage gateway activation, cache upload buffer, nfs smb file share, iscsi target, vtl tape, bandwidth rate limit.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with storagegateway and ec2 access. Works with Terraform aws_storagegateway_gateway, aws_storagegateway_nfs_file_share, aws_storagegateway_smb_file_share, aws_storagegateway_cached_iscsi_volume, aws_storagegateway_stored_iscsi_volume, and aws_storagegateway_tape_pool resources, and CloudFormation AWS::StorageGateway templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, storage-gateway, s3-file-gateway, volume-gateway, tape-gateway, cloudops, deploy, storage, provisioning, nfs, smb, iscsi
  dependencies: aws-orchestrator
  keywords: aws, storage gateway, s3 file gateway, volume gateway, tape gateway, fsx file gateway, cloudops, deploy, provisioning, cache, upload buffer, nfs, smb, iscsi, vtl, active directory, bandwidth rate limit, file share
  when_to_use: Invoke when the user wants to deploy an AWS Storage Gateway (S3 File Gateway, FSx File Gateway, Volume Gateway cached or stored, or Tape Gateway), activate a gateway, allocate local disks (cache vs upload buffer), configure NFS or SMB file shares, join an SMB file share to Active Directory, set up iSCSI volumes, configure a VTL for backup software, apply bandwidth rate limits, or configure CloudWatch monitoring and audit logging. Do NOT invoke for AWS DataSync (use datasync skills), AWS Transfer Family (SFTP), or S3 File Gateway troubleshooting (use a troubleshooter skill).
---

# Storage Gateway Deployer

An AWS CloudOps agent skill that deploys AWS Storage Gateway with
correct production defaults. The skill walks the operator through
gateway type selection (S3 File, FSx File, Volume, Tape), gateway
activation via activation key, local disk allocation (cache vs upload
buffer), file share configuration (NFS/SMB, S3 bucket mapping,
default storage class), SMB Active Directory integration, Volume
Gateway iSCSI targets, Tape Gateway VTL, bandwidth rate limits,
CloudWatch monitoring, and audit logging. It captures the deployment
topology, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

deploy Storage Gateway, S3 File Gateway, FSx File Gateway, Volume
Gateway cached, Volume Gateway stored, Tape Gateway VTL, Storage
Gateway activation key, cache vs upload buffer, NFS file share, SMB
file share, iSCSI target, bandwidth rate limit, SMB Active Directory,
file share refresh, Storage Gateway audit logging.

## STRICT output contract

When this skill is invoked with a Storage Gateway deployment request
(deploy a gateway, configure a file share, set up iSCSI volumes,
deploy a VTL, or a partial configuration), the agent MUST respond with
the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `STORAGE_GATEWAY:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as the
first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from
the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Gateway type selection | Core decision: S3 File vs FSx File vs Volume vs Tape |
| Step 2 — Gateway activation (activation key) | Required for all gateway types |
| Step 3 — Local disk allocation (cache vs upload buffer) | Storage sizing |
| Step 4 — S3 File Gateway NFS/SMB file shares | File share setup |
| Step 5 — SMB Active Directory integration | Domain-joined SMB |
| Step 6 — Volume Gateway iSCSI targets | Block storage |
| Step 7 — Tape Gateway VTL | Backup software integration |
| Step 8 — Bandwidth rate limits | Upload throttling |
| Step 9 — CloudWatch monitoring and audit logging | Observability |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/cache-and-buffer-sizing.md | Cache + buffer detail |
| references/file-share-and-smb.md | File share + SMB/AD detail |

## Mindset

**One-line takeaway:** Storage Gateway bridges on-premises
applications with AWS cloud storage. The gateway type determines the
interface (file, block, or tape). Cache stores hot data locally for
low-latency access; the upload buffer queues data waiting to upload
to AWS. Both must be sized independently — the cache is NOT the
upload buffer.

Three misconceptions dominate Storage Gateway misdesign at provisioning
time:

- **"Cache and upload buffer are the same thing."** They are NOT.
  The cache holds recently accessed data for low-latency reads (S3
  File Gateway, Volume Gateway cached mode). The upload buffer holds
  data that has been written locally but not yet uploaded to AWS. In
  Volume Gateway stored mode, there is NO cache — only the upload
  buffer (the local disk IS the primary copy). Conflating the two
  leads to undersized buffers (data upload stalls) or undersized
  caches (read latency spikes).

- **"The gateway region must match the on-premises data center
  location."** The gateway region must match the S3 bucket (or FSx
  filesystem, or backup target) region — NOT the physical location of
  the on-premises host. A gateway in us-east-1 serves data to S3
  buckets in us-east-1 regardless of where the hardware sits. Mismatched
  regions cause cross-region data transfer charges and increased
  latency.

- **"SMB file shares do not need Active Directory."** For guest access,
  a simple SMB share with a guest password works. But for any
  production environment with existing AD infrastructure, the gateway
  must be joined to Active Directory for authenticated access, audit
  logging per user, and NTFS ACL enforcement. Deploying SMB without AD
  in a domain environment forces guest-only access, which is insecure
  and loses per-user visibility.

## Configuration dependency graph (novel heuristic)

Storage Gateway configurations are NOT independent. The gateway must
be activated before disks can be allocated. File shares require the
gateway to be running and connected. SMB AD join requires the gateway
to be activated first. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Gateway VM (on-premises host) | hypervisor (VMware, Hyper-V, KVM) or hardware appliance; network connectivity to AWS | gateway cannot be activated without first connecting to the activation endpoint via HTTPS (port 443) | activation key |
| Activation key | gateway VM is running and connected; AWS region selected | activation key expires after a short window; must be used immediately to create the gateway | the gateway resource in AWS |
| Gateway resource (activate_gateway) | valid activation key; gateway name; gateway time zone | gateway type is set at activation and CANNOT be changed later (must delete and recreate) | all downstream configurations |
| Local disk — cache | gateway activated; physical disks available on the host | cache size affects read latency; too small = frequent S3 fetches | S3 File Gateway reads, Volume Gateway cached reads |
| Local disk — upload buffer | gateway activated; physical disks available on the host | buffer too small = writes block when buffer is full; data upload stalls | all write operations |
| S3 File Gateway NFS file share | gateway activated; S3 bucket exists; IAM role with S3 access | bucket region should match gateway region for performance | NFS client access to S3 data |
| S3 File Gateway SMB file share | gateway activated; S3 bucket exists; IAM role; AD join (optional but recommended for production) | without AD join, only guest access; with AD, per-user audit logging | SMB client access to S3 data |
| Volume Gateway iSCSI volume | gateway activated; upload buffer allocated; (cache for cached mode) | cached mode: cache + buffer; stored mode: buffer only (local disk is primary) | iSCSI initiator connections |
| Tape Gateway VTL | gateway activated; upload buffer allocated; cache allocated; tape pool configured | backup software (Veeam, NetBackup, etc.) must discover the VTL tapes | backup software integration |
| Bandwidth rate limits | gateway activated | schedule-based limits throttle during business hours, lift off-hours | upload throttling |
| CloudWatch alarms | gateway activated; CloudWatch enabled | without CloudWatch, gateway health and throughput are invisible | monitoring and alerting |

**The cache-vs-upload-buffer row is the one a baseline model misses.**
A naive deployment allocates one local disk and calls it "cache" without
distinguishing cache from upload buffer. This works for small test
deployments but fails at scale: the upload buffer fills up and writes
stall, or the cache is too small and every read triggers an S3 fetch.
The procedure below forces an explicit decision on each.

**Cross-dependency gotchas:**
- The gateway type (FILE_S3, FILE_FSX, VOLUME, VTL) is set at activation
  and CANNOT be changed. To switch types, delete the gateway and
  recreate with a new activation key.
- S3 File Gateway file shares should map to S3 buckets in the SAME
  region as the gateway to avoid cross-region transfer costs.
- Volume Gateway stored mode does NOT use a cache — the local disk IS
  the primary storage. Only cached mode uses a cache.
- SMB AD join must be done AFTER gateway activation but BEFORE creating
  authenticated SMB file shares. Guest shares work without AD.
- Bandwidth rate limits apply to ALL traffic (uploads and downloads).
  Schedule them to lift off-hours for faster sync.

## Expert heuristic: cache vs upload buffer sizing

A baseline model says "allocate local disks." The correct heuristic
recognizes that cache and upload buffer serve fundamentally different
purposes and must be sized independently.

```text
Cache (S3 File Gateway, Volume Gateway cached mode):
  Purpose: store recently accessed data for low-latency reads
  Sizing rule: cache should hold the "working set" of hot data
    ├── Typical: 10-20% of total dataset for active workloads
    ├── Minimum: 150 GB (hard floor)
    └── More cache = fewer S3 fetches = lower latency + lower S3 GET costs

Upload Buffer (ALL gateway types):
  Purpose: queue data written locally that is waiting to upload to AWS
  Sizing rule: buffer should hold data generated between upload cycles
    ├── Typical: 1.5x the estimated daily data change rate
    ├── Minimum: 150 GB (hard floor)
    └── Too small = writes block when buffer is full (application stalls)

Volume Gateway stored mode:
  ├── NO cache (the local disk IS the primary copy)
  ├── Upload buffer still needed (async replication to AWS)
  └── Local disk sizing = full primary dataset + upload buffer
```

**Key implication:** the #1 cause of "my Storage Gateway is slow" is
an undersized cache (read-heavy workloads) or an undersized upload
buffer (write-heavy workloads). Always size them independently based
on the workload's read/write characteristics.

## Expert heuristic: S3 File Gateway region alignment with S3 bucket

The gateway region must match the S3 bucket region. A gateway in
us-east-1 that serves data from an S3 bucket in eu-west-1 incurs
cross-region data transfer charges for every read and write.

```text
Gateway region vs S3 bucket region:
  ├── Same region → no cross-region charges, lowest latency
  │     Gateway in us-east-1, bucket in us-east-1 ✓
  ├── Different region → cross-region transfer charges ($0.02/GB)
  │     Gateway in us-east-1, bucket in eu-west-1 ✗
  └── Fix: redeploy gateway in the bucket's region, or replicate
        the bucket to the gateway's region
```

**Key implication:** always verify the S3 bucket region matches the
gateway region before creating file shares. Cross-region mismatch is a
silent cost drain.

## Expert heuristic: bandwidth throttle scheduling

Bandwidth rate limits can be scheduled to throttle during business
hours and lift during off-hours, preventing the gateway from
saturating the on-premises internet link during peak usage.

```text
Bandwidth schedule strategy:
  ├── Business hours (09:00-18:00): throttle to 50 Mbps
  ├── Off-hours (18:00-09:00): lift to 500 Mbps (or unlimited)
  └── Weekend: unlimited (bulk data migration windows)
```

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| On-premises host (VMware/Hyper-V/KVM) or hardware appliance | Gateway VM must run on a supported hypervisor | Confirm hypervisor type and version |
| Network connectivity to AWS | Gateway needs HTTPS (port 443) to AWS endpoints | Verify firewall allows outbound 443 |
| S3 bucket exists (S3 File Gateway) | File shares map to S3 buckets | `aws s3api head-bucket --bucket <name>` |
| S3 bucket region identified | Gateway region should match bucket region | `aws s3api get-bucket-location --bucket <name>` |
| IAM role with S3/FSx/CloudWatch permissions | Gateway needs permissions to access backend storage | Verify IAM role policy |
| Activation key (from gateway VM console) | Required to activate the gateway in AWS | Obtain from gateway VM activation URL |
| Local disk capacity known | Cache and upload buffer must be sized | Assess physical disk capacity on host |
| Active Directory details (if SMB with AD) | Domain join requires domain name, OU, credentials | Confirm AD connectivity and service account |
| VPC/subnet for gateway ENI (if applicable) | Gateway needs network interface in AWS | `aws ec2 describe-subnets` |
| Backup software compatibility (Tape Gateway) | VTL must be supported by backup software | Check compatibility matrix (Veeam, NetBackup, etc.) |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Gateway type selection

Storage Gateway supports four gateway types. The type is set at
activation and CANNOT be changed later.

| Gateway type | Interface | Use case | Backend storage |
|---|---|---|---|
| S3 File Gateway (`FILE_S3`) | NFS / SMB file | On-prem apps needing S3 object storage via file protocol | Amazon S3 |
| FSx File Gateway (`FILE_FSX`) | NFS / SMB file | On-prem apps needing Windows file shares with AD integration | Amazon FSx for Windows File Server |
| Volume Gateway — Cached (`STORED` n/a, `CACHED`) | iSCSI block | On-prem apps needing block storage with cloud-backed primary | Amazon EBS snapshots |
| Volume Gateway — Stored (`STORED`) | iSCSI block | On-prem apps needing low-latency primary storage with async cloud backup | Amazon EBS snapshots |
| Tape Gateway (`VTL`) | iSCSI tape (VTL) | Backup software needing tape-based backup with cloud storage | Amazon S3 / S3 Glacier |

**Gateway type is immutable after activation.** To change types, delete
the gateway and create a new one with a new activation key.

## Step 2 — Gateway activation (activation key)

After deploying the gateway VM on-premises (or the hardware appliance),
the gateway VM provides an activation URL. Connecting to this URL
generates an activation key, which is used to activate the gateway in
AWS.

```bash
# Activate the gateway (requires activation key from gateway VM console)
ACTIVATION_KEY="XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"

aws storagegateway activate-gateway \
  --activation-key "$ACTIVATION_KEY" \
  --gateway-name "prod-s3-file-gateway" \
  --gateway-timezone "GMT-5:00" \
  --gateway-region us-east-1 \
  --gateway-type FILE_S3 \
  --tags Key=Environment,Value=production \
  --region us-east-1
```

**Verify the gateway is running:**

```bash
aws storagegateway describe-gateway-information \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --region us-east-1
# Expected: GatewayState: "RUNNING"
```

**Common mistake:** trying to configure file shares or volumes before
the gateway state is `RUNNING`. All downstream operations fail until
the gateway is fully activated.

## Step 3 — Local disk allocation (cache vs upload buffer)

After activation, allocate local disks on the gateway host. The
gateway discovers available disks; the operator assigns them as cache
or upload buffer.

```bash
# List local disks discovered by the gateway
aws storagegateway list-local-disks \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --region us-east-1

# Allocate a disk as cache
aws storagegateway add-cache \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --disk-ids ami-xxxx \
  --region us-east-1

# Allocate a disk as upload buffer
aws storagegateway add-upload-buffer \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --disk-ids ami-yyyy \
  --region us-east-1
```

**Critical sizing rules:**
- Cache: 150 GB minimum; size for the working set of hot data (10-20%
  of total dataset for active workloads).
- Upload buffer: 150 GB minimum; size for 1.5x the estimated daily data
  change rate.
- Volume Gateway stored mode: NO cache needed (local disk is primary).
- Use separate physical disks for cache and upload buffer for
  performance isolation.

## Step 4 — S3 File Gateway NFS/SMB file shares

S3 File Gateway exposes S3 buckets as NFS or SMB file shares.

**Create an NFS file share:**

```bash
aws storagegateway create-nfs-file-share \
  --client-token unique-token-12345 \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --role arn:aws:iam::123456789012:role/StorageGatewayS3Role \
  --location-arn arn:aws:s3:::my-data-bucket \
  --default-storage-class S3_STANDARD \
  --client-list 10.0.0.0/16 10.1.0.0/16 \
  --squash NoRootSquash \
  --region us-east-1
```

**Create an SMB file share (guest access):**

```bash
aws storagegateway create-smb-file-share \
  --client-token unique-token-67890 \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --role arn:aws:iam::123456789012:role/StorageGatewayS3Role \
  --location-arn arn:aws:s3:::my-data-bucket \
  --default-storage-class S3_STANDARD \
  --guest-password "MyGuestPass123!" \
  --authentication GuestAccess \
  --region us-east-1
```

**File share configuration:**
- `--default-storage-class`: S3_STANDARD (default), S3_STANDARD_IA,
  S3_INTELLIGENT_TIERING, S3_GLACIER_IR. Choose based on access patterns.
- `--client-list` (NFS): restrict to known CIDR blocks for security.
- `--object-acl`: public-read-write, private (default). Use private
  unless explicitly needed.
- File shares support automatic refresh to detect objects added to S3
  directly (outside the gateway).

## Step 5 — SMB Active Directory integration

For production SMB file shares, join the gateway to Active Directory.
This enables authenticated access, per-user audit logging, and NTFS
ACL enforcement.

```bash
# Join the gateway to Active Directory
aws storagegateway join-domain \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --domain-name corp.example.com \
  --organizational-unit "OU=Servers,DC=corp,DC=example,DC=com" \
  --domain-username sgw-service \
  --domain-password "DomainPass123!" \
  --region us-east-1
```

**After AD join, create authenticated SMB file shares:**

```bash
aws storagegateway create-smb-file-share \
  --client-token unique-token-auth-12345 \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --role arn:aws:iam::123456789012:role/StorageGatewayS3Role \
  --location-arn arn:aws:s3:::my-data-bucket \
  --default-storage-class S3_STANDARD \
  --authentication ActiveDirectory \
  --admin-user-list "corp\\sgw-admins" \
  --region us-east-1
```

**Prerequisites for AD join:**
- DNS resolution: the gateway must resolve the domain controller.
- Network connectivity: ports 53 (DNS), 88 (Kerberos), 389 (LDAP),
  445 (SMB), 464 (Kerberos password), 3268 (LDAP GC) must be open.
- Service account with domain join permissions.

## Step 6 — Volume Gateway iSCSI targets

Volume Gateway exposes block storage via iSCSI. Cached mode uses cache
+ upload buffer; stored mode uses the local disk as primary with upload
buffer for async replication.

**Create a cached iSCSI volume:**

```bash
aws storagegateway create-cached-iscsi-volume \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --volume-size-in-bytes 1073741824000 \
  --target-name prod-volume-01 \
  --network-interface-id eni-xxxx \
  --client-token unique-token-vol-12345 \
  --region us-east-1
```

**Create a stored iSCSI volume (local disk is primary):**

```bash
aws storagegateway create-stored-iscsi-volume \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --disk-id ami-zzzz \
  --preserve-existing-data false \
  --target-name prod-stored-volume-01 \
  --network-interface-id eni-xxxx \
  --client-token unique-token-stored-12345 \
  --region us-east-1
```

**Connect from the iSCSI initiator (on-premises client):**

```bash
# Discover the iSCSI target
iscsiadm --mode discovery --type sendtargets --portal <gateway-ip> --discover

# Login to the target
iscsiadm --mode node --targetname iqn.1997-05.com.amazon:prod-volume-01 \
  --portal <gateway-ip>:3260 --login
```

## Step 7 — Tape Gateway VTL

Tape Gateway presents a Virtual Tape Library (VTL) to backup software
via iSCSI. Backup software (Veeam, NetBackup, Commvault, etc.)
discovers the VTL and writes backups to virtual tapes.

```bash
# The VTL is auto-created on Tape Gateway activation
# Create a tape pool for retention management
aws storagegateway create-tape-pool \
  --pool-name "GlacierPool" \
  --storage-class GLACIER \
  --retention-lock-type governance \
  --retention-lock-time-in-days 365 \
  --region us-east-1

# Create virtual tapes
aws storagegateway create-tapes \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --tape-size-in-bytes 1073741824000 \
  --client-token unique-token-tape-12345 \
  --num-tapes-to-create 10 \
  --tape-barcode-prefix "TAPE" \
  --pool-id GlacierPool \
  --region us-east-1
```

**Backup software configuration:**
- Configure the backup software to connect to the Tape Gateway via
  iSCSI (same as connecting to a physical tape library).
- The VTL appears as a physical tape library with a medium changer and
  tape drives.
- Tapes are automatically archived to S3 Glacier or Deep Archive based
  on the tape pool configuration.

## Step 8 — Bandwidth rate limits

Bandwidth rate limits control how much network bandwidth the gateway
uses for uploading data to AWS. They can be scheduled by time of day.

```bash
# Set a bandwidth rate limit schedule
aws storagegateway update-bandwidth-rate-limit-schedule \
  --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-XXXXX \
  --bandwidth-rate-limit-schedules \
    StartHourOfDay=9,BandwidthRateLimitIntervals=[{StartHourOfDay=9,EndHourOfDay=18,BitsPerSecondLimit=50000000}], \
    StartHourOfDay=18,BandwidthRateLimitIntervals=[{StartHourOfDay=18,EndHourOfDay=9,BitsPerSecondLimit=500000000}] \
  --region us-east-1
```

**Scheduling strategy:**
- Business hours: throttle to prevent saturation of the internet link.
- Off-hours: lift or remove the limit for faster sync.
- Weekend: consider unlimited for bulk migration windows.

## Step 9 — CloudWatch monitoring and audit logging

Enable CloudWatch metrics and audit logging for observability.

**Key CloudWatch metrics to monitor:**

| Metric | What it tells you | Alarm threshold |
|---|---|---|
| `CacheHitPercent` | Cache effectiveness (S3 File, Volume cached) | < 80% → cache too small |
| `UploadBufferPercentUsed` | Upload buffer utilization | > 80% → add more buffer |
| `CloudBytesUploaded` | Data uploaded to AWS | Trend for capacity planning |
| `TotalCacheSize` | Current cache size | Verify after allocation |
| `WorkDays` | Gateway uptime | Monitor for unexpected downtime |

**Enable audit logging (SMB file shares):**

```bash
# Create a CloudWatch Logs log group for audit logs
aws logs create-log-group \
  --log-group-name /aws/storagegateway/sgw-XXXXX-audit \
  --region us-east-1

# Enable SMB audit logging on file shares (requires AD)
aws storagegateway update-smb-file-share \
  --file-share-arn arn:aws:storagegateway:us-east-1:123456789012:share/share-XXXXX \
  --audit-destination-arn arn:aws:logs:us-east-1:123456789012:log-group:/aws/storagegateway/sgw-XXXXX-audit \
  --region us-east-1
```

## Step 10 — Recent features

**Recent AWS features (2023-2026):**

- **FSx File Gateway deprecation (2024-2025):** AWS announced planned
  deprecation of FSx File Gateway. Evaluate Amazon FSx for Windows File
  Server with Direct Connect or VPN for new deployments.

- **S3 File Gateway SMB audit logging (2023-2024):** Enhanced audit
  logging for SMB shares joined to AD, providing per-user access logs.

- **File share automatic refresh improvements (2023-2024):** Improved
  automatic refresh of NFS and SMB file shares to detect objects
  written directly to S3 outside the gateway. Refresh can now be
  triggered on demand.

- **Volume Gateway performance improvements (2023-2024):** Increased
  throughput limits for cached and stored volumes, supporting higher
  IOPS for demanding on-premises applications.

- **Bandwidth rate limit scheduling (2023-2024):** Enhanced bandwidth
  scheduling with multiple time windows per day, allowing more
  granular throttling for business-hours vs off-hours.

- **Tape Gateway S3 Glacier Instant Retrieval (2024-2025):** Tape
  Gateway now supports archiving virtual tapes to S3 Glacier Instant
  Retrieval for faster restore of archived backup data.

- **Terraform provider maturity (2023-2024):** The Terraform
  `aws_storagegateway_*` resources support full lifecycle management
  including volumes, file shares, tape pools, and bandwidth schedules.

## NEVER do these things

1. **NEVER conflate cache and upload buffer.** They serve different
   purposes: cache = hot data for reads, upload buffer = write queue
   for uploads. Size them independently based on read/write workload
   characteristics.

2. **NEVER deploy a gateway in a different region from the S3 bucket.**
   Cross-region gateway-to-bucket communication incurs data transfer
   charges on every read and write. Always match the gateway region
   to the S3 bucket region.

3. **NEVER assume the gateway type can be changed after activation.**
   The type (FILE_S3, FILE_FSX, VOLUME, VTL) is immutable. To change
   types, delete the gateway and recreate with a new activation key.

4. **NEVER deploy SMB file shares without Active Directory in a domain
   environment.** Guest-only access loses per-user audit logging,
   NTFS ACL enforcement, and is insecure for production workloads.
   Join the gateway to AD before creating authenticated shares.

5. **NEVER use a single physical disk for both cache and upload buffer.**
   Cache and upload buffer have different I/O patterns (random reads
   vs sequential writes). Using separate physical disks provides
   performance isolation and prevents I/O contention.

6. **NEVER forget to allocate the upload buffer for Volume Gateway
   stored mode.** Stored mode uses the local disk as primary, but
   STILL needs an upload buffer for async replication to AWS. A missing
   buffer means no cloud backup.

7. **NEVER leave file share client lists unrestricted.** NFS file
   shares should restrict `--client-list` to known CIDR blocks. SMB
   shares should use AD authentication. Unrestricted shares are a
   security risk.

8. **NEVER ignore CloudWatch CacheHitPercent.** A low cache hit
   percentage means most reads require an S3 fetch, causing high
   latency and elevated S3 GET costs. Add cache capacity if
   CacheHitPercent drops below 80%.

9. **NEVER deploy Tape Gateway without verifying backup software
   compatibility.** The VTL must be supported by the backup software
   (Veeam, NetBackup, Commvault, Backup Exec, etc.). Check the
   compatibility matrix before deployment.

10. **NEVER forget to schedule bandwidth rate limits.** Without
    throttling, the gateway can saturate the on-premises internet link
    during business hours. Schedule limits for business hours and lift
    them off-hours.

## Output format

```text
STORAGE_GATEWAY: <gateway-name> (<gateway-type>) — <gateway-arn>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Gateway type: S3 File Gateway | FSx File Gateway | Volume Gateway (Cached) | Volume Gateway (Stored) | Tape Gateway
  [✓|✗] Activation: <gateway-arn> — RUNNING
  [✓|✗] Gateway region: <region> (matches S3 bucket region: <bucket-region>)
  [✓|✗] Cache: <disk-id> (<size> GB) — allocated
  [✓|✗] Upload buffer: <disk-id> (<size> GB) — allocated
  [✓|✗] S3 bucket: <bucket-name> (region: <region>)
  [✓|✗] IAM role: <role-arn> (S3 access confirmed)
  [✓|✗] File share (NFS): <share-arn> → s3://<bucket> (clients: <cidr-list>)
  [✓|✗] File share (SMB): <share-arn> → s3://<bucket> (auth: ActiveDirectory | GuestAccess)
  [✓|✗] Active Directory: joined (domain: <domain-name>) | not applicable
  [✓|✗] iSCSI volume: <volume-arn> (<target-name>, <size> GB)
  [✓|✗] Tape Gateway VTL: <tape-count> tapes (<tape-size> GB each), pool: <pool-name>
  [✓|✗] Bandwidth rate limit: scheduled (business: <rate>, off-hours: <rate>)
  [✓|✗] CloudWatch: CacheHitPercent alarm at <threshold>
  [✓|✗] Audit logging: CloudWatch Logs (<log-group>) | disabled
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws storagegateway describe-gateway-information --gateway-arn <gateway-arn> --region <region>
  aws storagegateway list-file-shares --gateway-arn <gateway-arn> --region <region>
  aws storagegateway list-volumes --gateway-arn <gateway-arn> --region <region>
```

### Worked example — S3 File Gateway with NFS file share

```text
STORAGE_GATEWAY: prod-s3-file-gateway (FILE_S3) — arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-AAAAA
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Gateway type: S3 File Gateway
  [✓] Activation: arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-AAAAA — RUNNING
  [✓] Gateway region: us-east-1 (matches S3 bucket region: us-east-1)
  [✓] Cache: disk-aaa (500 GB) — allocated
  [✓] Upload buffer: disk-bbb (300 GB) — allocated
  [✓] S3 bucket: my-data-bucket (region: us-east-1)
  [✓] IAM role: arn:aws:iam::123456789012:role/StorageGatewayS3Role
  [✓] File share (NFS): arn:aws:storagegateway:us-east-1:123456789012:share/share-AAAAA → s3://my-data-bucket (clients: 10.0.0.0/16)
  [✓] Default storage class: S3_STANDARD
  [✓] Bandwidth rate limit: scheduled (business: 50 Mbps, off-hours: 500 Mbps)
  [✓] CloudWatch: CacheHitPercent alarm at 80%
  [✓] Tags: Environment=production, Application=file-sharing
VERIFICATION_COMMANDS:
  aws storagegateway describe-gateway-information --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-AAAAA --region us-east-1
  aws storagegateway list-file-shares --gateway-arn arn:aws:storagegateway:us-east-1:123456789012:gateway/sgw-AAAAA --region us-east-1
```

## Error handling

### Gateway activation fails — invalid activation key
- The activation key expires shortly after generation. Reconnect to
  the gateway VM activation endpoint to generate a new key, then
  retry `activate-gateway` immediately.

### File share creation fails — IAM role missing S3 permissions
- The IAM role must have `s3:GetObject`, `s3:PutObject`,
  `s3:DeleteObject`, and `s3:ListBucket` on the target bucket. Add
  the required policy and retry.

### SMB AD join fails — domain unreachable
- Verify DNS resolution of the domain controller, network ports
  53/88/389/445/464/3268, and service account domain-join perms.

### Volume Gateway iSCSI connection fails
- Verify the iSCSI initiator can reach the gateway IP on port 3260.
  Run `iscsiadm --mode discovery` to verify target visibility.

### CacheHitPercent alarm fires
- The cache is too small for the working set. Double the cache size
  via `add-cache` and re-evaluate after 24 hours.

### Upload buffer full — writes blocked
- The upload buffer is undersized. Add more disks via
  `add-upload-buffer`. Check if bandwidth limits are throttling uploads.

## Domain

AWS CloudOps / AWS Storage Gateway Provisioning & Hybrid Cloud Storage.

## AWS documentation

- **Storage Gateway User Guide** — https://docs.aws.amazon.com/storagegateway/latest/userguide/WhatIsStorageGateway.html
- **Activate a gateway** — https://docs.aws.amazon.com/storagegateway/latest/userguide/get-activation-key.html
- **S3 File Gateway** — https://docs.aws.amazon.com/storagegateway/latest/userguide/create-gateway-file.html
- **Tape Gateway** — https://docs.aws.amazon.com/storagegateway/latest/userguide/TapeGateway.html
- **Local disks** — https://docs.aws.amazon.com/storagegateway/latest/userguide/understanding-local-disk.html
- **Bandwidth limits** — https://docs.aws.amazon.com/storagegateway/latest/userguide/ManagingGatewayBandwidth.html
- **SMB AD** — https://docs.aws.amazon.com/storagegateway/latest/userguide/smb-active-directory.html
- **CloudWatch** — https://docs.aws.amazon.com/storagegateway/latest/userguide/monitoring-cloudwatch.html
