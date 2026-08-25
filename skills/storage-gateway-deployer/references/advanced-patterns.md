# Advanced Patterns — Storage Gateway Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Skill overview (intro)

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

## Tape Gateway backup software configuration

- Configure the backup software to connect to the Tape Gateway via
  iSCSI (same as connecting to a physical tape library).
- The VTL appears as a physical tape library with a medium changer and
  tape drives.
- Tapes are automatically archived to S3 Glacier or Deep Archive based
  on the tape pool configuration.

## Bandwidth rate limit scheduling strategy

- Business hours: throttle to prevent saturation of the internet link.
- Off-hours: lift or remove the limit for faster sync.
- Weekend: consider unlimited for bulk migration windows.

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
