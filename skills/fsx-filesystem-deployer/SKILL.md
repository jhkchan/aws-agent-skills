---
name: fsx-filesystem-deployer
description: >-
  Provisions Amazon FSx file systems with production defaults:
  FSx for Windows (storage type SSD/HDD, throughput capacity,
  deployment Multi-AZ/Single-AZ, AD integration, DNS aliases,
  shadow copies, dedup, backups), FSx for Lustre (PERSISTENT/
  SCRATCH, SSD/HDD, metadata config, S3 export, compression),
  FSx for ONTAP (SVM, volume tiering), FSx for OpenZFS, KMS
  encryption, backup/restore, IOPS, maintenance window. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when
  creating FSx for Windows, FSx for Lustre, FSx for ONTAP, or
  FSx for OpenZFS. Triggers: create fsx windows, fsx lustre, fsx
  ontap, fsx openzfs, multi-az file system, fsx backup, s3 export
  lustre, dedup, throughput capacity.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with fsx and ec2
  access (and ds access for AD-integrated Windows deployments).
  Works with Terraform aws_fsx_windows_file_system /
  aws_fsx_lustre_file_system / aws_fsx_ontap_file_system /
  aws_fsx_openzfs_file_system resources and CloudFormation
  AWS::FSx::FileSystem templates.
keywords:
  - aws
  - fsx
  - fsx for windows
  - fsx for lustre
  - fsx for ontap
  - fsx for openzfs
  - cloudops
  - deploy
  - provisioning
  - multi-az
  - single-az
  - throughput capacity
  - dedup
  - s3 export
  - kms encryption
tags:
  - aws
  - fsx
  - storage
  - cloudops
  - deploy
  - provisioning
  - multi-az
  - throughput-capacity
  - dedup
  - kms-encryption
  - backup
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - fsx
    - storage
    - cloudops
    - deploy
    - provisioning
    - multi-az
    - throughput-capacity
    - dedup
    - kms-encryption
    - backup
  dependencies:
    - aws-orchestrator
  keywords:
    - create fsx windows
    - fsx lustre
    - fsx ontap
    - fsx openzfs
    - multi-az file system
    - fsx backup
    - s3 export lustre
    - dedup
    - throughput capacity
  when_to_use: >-
    Invoke when the user wants to create an Amazon FSx file system
    (FSx for Windows, FSx for Lustre, FSx for ONTAP, or FSx for
    OpenZFS), configure Multi-AZ vs Single-AZ deployment, set up AD
    integration for Windows file systems, configure S3 export for
    Lustre, enable dedup, configure backups, or set throughput
    capacity. Do NOT invoke for EFS, EBS, or S3 (use the relevant
    storage skills).
---

# FSx Filesystem Deployer

An AWS CloudOps agent skill that provisions Amazon FSx file systems
with correct defaults. The skill walks the operator through file
system type selection (Windows, Lustre, ONTAP, OpenZFS), storage
type (SSD/HDD), deployment type (Multi-AZ/Single-AZ), throughput
capacity, AD integration, DNS aliases, shadow copies, dedup,
backups, S3 export for Lustre, KMS encryption, and maintenance
windows, captures all configuration decisions, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create FSx for Windows, FSx for Lustre, FSx for ONTAP, FSx for
OpenZFS, Multi-AZ file system, FSx backup, S3 export Lustre, dedup,
throughput capacity, KMS encryption FSx.

## STRICT output contract

When this skill is invoked with an FSx provisioning request (create
an FSx file system, configure Multi-AZ/Single-AZ, set up AD
integration, configure S3 export, enable dedup, or set throughput
capacity, or a partial configuration), the agent MUST respond with
the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `FSX_FILESYSTEM:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — File system type selection (Windows vs Lustre vs ONTAP vs OpenZFS) | Core type decision |
| Step 2 — Storage type and throughput capacity | Performance planning |
| Step 3 — Deployment type (Multi-AZ vs Single-AZ) | Availability planning |
| Step 4 — AD integration and DNS aliases (Windows) | Windows-specific |
| Step 5 — S3 export for Lustre | Lustre-specific |
| Step 6 — Dedup, shadow copies, and data management | Storage efficiency |
| Step 7 — KMS encryption | Security |
| Step 8 — Backup and restore | Backup and DR |
| Step 9 — ONTAP SVM and volume tiering | ONTAP-specific |
| Step 10 — Maintenance windows | Operational |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/windows-and-lustre.md | Windows + Lustre detail |
| references/ontap-and-backup.md | ONTAP + backup detail |

## Mindset

**One-line takeaway:** Amazon FSx provides four file system types —
FSx for Windows (SMB/CIFS with AD), FSx for Lustre (HPC POSIX),
FSx for ONTAP (NetApp multi-protocol), and FSx for OpenZFS (ZFS
POSIX). Each type has distinct storage types (SSD/HDD), deployment
options (Multi-AZ/Single-AZ), throughput tiers, and integration
surfaces. Multi-AZ provides automatic failover. Throughput capacity
is stepped (not arbitrary). S3 export links Lustre to S3. Dedup
saves 50-80% on Windows file shares with repetitive data.

Three misconceptions dominate FSx misdesign at provisioning time:

- **"Multi-AZ and Single-AZ are the same with different labels."**
  They are NOT. Multi-AZ provides automatic failover to a standby
  in a different AZ (sub-minute failover for Windows, transparent
  for ONTAP). Single-AZ has a single instance with automated backups
  for recovery. Multi-AZ costs ~2x but provides near-zero RPO.
  Choose Multi-AZ for production workloads requiring high
  availability.

- **"Throughput capacity can be set to any value."** It CANNOT.
  Throughput capacity is stepped (e.g., 8, 16, 32, 64, 128, 256,
  512, 1024, 2048 MB/s for Windows). A baseline model picks an
  arbitrary number. The correct approach selects the nearest step
  above the workload requirement, considering that higher throughput
  also costs more per hour.

- **"S3 export on Lustre means data lives in S3."** It does NOT.
  S3 export creates a LINK between the Lustre file system and an S3
  bucket. Data is imported from S3 into Lustre on access and
  exported back to S3 on write or via a background job. The Lustre
  file system itself uses SSD/HDD storage. S3 is the backing store,
  not the file system.

## Configuration dependency graph (novel heuristic)

FSx configurations are NOT independent. The file system type
determines what storage types, deployment types, and features are
available. AD integration requires a directory in ACTIVE state.
S3 export requires an S3 bucket with appropriate permissions. Use
this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| FSx for Windows | 2 subnets in different AZs (Multi-AZ); Active Directory | storage type CANNOT be changed after creation; throughput CAN be changed | SMB file share |
| FSx for Lustre | VPC with subnets; S3 bucket (for S3-linked) | deployment type (PERSISTENT vs SCRATCH) CANNOT be changed; scratch file systems are EPHEMERAL | HPC POSIX storage |
| FSx for ONTAP | 2 subnets in different AZs (Multi-AZ) | SVM and volumes must be created after file system is ACTIVE | multi-protocol (NFS/SMB/iSCSI) |
| FSx for OpenZFS | VPC with subnets | throughput capacity CAN be changed but requires a maintenance window | NFS POSIX storage |
| AD integration (Windows) | Managed AD or AD Connector in ACTIVE state | wrong directory = domain join fails silently | Windows authentication |
| Multi-AB deployment | 2 subnets in different AZs | Multi-AZ CANNOT be changed to Single-AZ after creation (or vice versa) | automatic failover |
| Throughput capacity | file system ACTIVE | changes cause a brief I/O suspension; stepped values only | performance tier |
| S3 export (Lustre) | S3 bucket exists; correct IAM permissions | wrong bucket policy = import/export silently fails | S3-backed Lustre |
| Dedup (Windows) | file system ACTIVE | dedup runs on a schedule; savings depend on data patterns | storage savings 50-80% |
| KMS encryption | KMS key exists (customer-managed or AWS-managed) | KMS key CANNOT be changed after creation | encryption at rest |
| Backup | file system ACTIVE; backup schedule configured | backups are application-consistent for Windows; manual backups persist after deletion | point-in-time recovery |

**The Multi-AZ-vs-Single-AZ row is the one a baseline model
misses.** Choosing Single-AZ for a production workload that needs
high availability is a costly mistake that requires recreating the
file system. The throughput-capacity stepping is another commonly
misconfigured item. The procedure below forces an explicit decision
on each.

**Cross-dependency gotchas:**
- Multi-AZ requires 2 subnets in DIFFERENT AZs. Single-AZ needs
  only 1 subnet.
- AD integration requires the directory to be ACTIVE before creating
  the file system. Creating a file system against a CREATING or
  FAILED directory produces a domain-join failure.
- S3 export for Lustre requires the S3 bucket to be in the SAME
  region as the file system.
- Dedup savings depend on data patterns (repetitive data = higher
  savings). File shares with lots of duplicated documents see
  50-80% savings; unique binary data sees near zero.
- KMS encryption key cannot be changed after creation. Choose
  customer-managed key for audit/control, or AWS-managed for
  simplicity.

## Expert heuristic: Multi-AZ vs Single-AZ failover pairing

A baseline model says "pick Single-AZ to save cost." The correct
heuristic recognizes that the deployment type depends on the RPO/RTO
requirements and workload criticality.

```text
Workload availability requirements:
  ├── Production, high-availability, RPO ≈ 0
  │     → Multi-AZ (automatic failover, standby in different AZ)
  │       Cost: ~2x Single-AZ
  │       Failover: automatic, sub-minute (Windows), transparent (ONTAP)
  │
  ├── Production, can tolerate brief downtime
  │     → Single-AZ with automated backups (backup window: minutes-hours)
  │       Cost: 1x
  │       Recovery: from backup (RPO = last backup, RTO = restore time)
  │
  ├── Dev/test, ephemeral, or non-critical
  │     → Single-AZ (lowest cost)
  │       Or SCRATCH deployment for Lustre (ephemeral, no replication)
  │
  └── HPC / burst, data in S3
        → FSx for Lustre SCRATCH (ephemeral) or PERSISTENT (durable)
          SCRATCH: no replication; data lost on deletion
          PERSISTENT: replicated within AZ; survives server failures
```

**Key implication:** Multi-AZ CANNOT be changed to Single-AZ after
creation (or vice versa). Getting this wrong means recreating the
file system. Always choose Multi-AZ for production workloads with
strict availability requirements.

## Expert heuristic: throughput capacity step sizing

Throughput capacity is NOT arbitrary. It comes in discrete steps.
Picking the right step avoids overpaying for unused capacity or
underprovisioning performance.

```text
FSx for Windows throughput capacity steps (MB/s):
  8, 16, 32, 64, 128, 256, 512, 1024, 2048

FSx for Lustre throughput (per TB of storage):
  50, 100, 200 MB/s per TB (HDD-based)
  125, 250, 500, 1000 MB/s per TB (SSD-based)

Selection heuristic:
  1. Measure or estimate peak workload throughput (MB/s)
  2. Select the nearest step ABOVE the requirement
  3. Leave 20-30% headroom for growth
  4. If between two steps, pick the higher one
     (upgrading requires a maintenance window; downtime cost > step cost delta)

  Example: workload needs 180 MB/s
    → Step above: 256 MB/s (Windows) or 200 MB/s/TB (Lustre HDD)
    → Leave headroom: 256 MB/s gives 30% headroom over 180
    → DO NOT pick 128 MB/s (below requirement → performance issues)
```

**Key implication:** throughput CAN be changed after creation for
most FSx types, but the change requires a brief I/O suspension or
maintenance window. Over-provisioning slightly is cheaper than
frequent upgrades.

## Expert heuristic: S3 export for Lustre

S3 export links a Lustre file system to an S3 bucket, enabling HPC
workloads to process data stored in S3 without manual transfers.

```text
S3-linked Lustre architecture:
  S3 Bucket (source of truth)
    ├── Import: S3 objects → Lustre files (lazy-loaded on first access)
    │     └── Metadata imported at file system creation
    └── Export: Lustre files → S3 objects (on write or via export job)
          └── Background sync or explicit aws fsx create-data-repository-task

  Deployment types for S3-linked:
    ├── SCRATCH_1: no replication, ephemeral, lowest cost
    ├── SCRATCH_2: partial replication for durability
    └── PERSISTENT: full replication, durable

  Import configuration:
    ├── NEW_FILES (import only files not already in Lustre)
    ├── CHANGED_FILES (re-import files that changed in S3)
    └── CHANGED_FILES_ALL (re-import everything)
```

**Key implication:** S3 export does NOT mean "data lives in S3." The
Lustre file system stores data on SSD/HDD. S3 is the backing data
repository for import/export. The file system must be in the SAME
region as the S3 bucket.

## Expert heuristic: dedup savings estimation

Dedup (FSx for Windows only) eliminates duplicate data blocks,
providing storage savings.

```text
Dedup savings estimation by workload type:
  ├── Windows file shares (user documents)
  │     Savings: 50-80% (lots of duplicate office documents)
  ├── Software deployment shares
  │     Savings: 30-70% (duplicate installers, package files)
  ├── Home directories
  │     Savings: 40-60% (duplicate user files, templates)
  └── Unique binary data (media, databases)
        Savings: 0-10% (no duplicates; dedup overhead may exceed savings)

  Configuration:
    DedupType:
      ├── GeneralPurpose — for general file shares (default)
      └── HyperV — for Hyper-V VM storage

    Schedule:
      └── Run during off-peak hours (e.g., nightly)
```

**Key implication:** dedup is NOT free — it uses CPU and I/O during
the dedup scan. Schedule it during off-peak hours. Estimate savings
based on data patterns before enabling.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| VPC with subnets (2 different AZs for Multi-AZ) | Multi-AZ requires cross-AZ subnets | `aws ec2 describe-subnets --filters Name=vpc-id,Values=<vpc>` |
| Active Directory ACTIVE (Windows) | FSx for Windows requires AD for authentication | `aws ds describe-directories` |
| S3 bucket exists (Lustre S3 export) | S3-linked Lustre requires a bucket | `aws s3api head-bucket --bucket <name>` |
| KMS key exists (if customer-managed) | Encryption requires a KMS key | `aws kms describe-key --key-id <key-id>` |
| Security group with required ports open | FSx needs specific ports for the protocol | Verify SG rules for SMB (445), NFS (2049), etc. |
| Correct throughput step selected | Throughput is stepped, not arbitrary | Match to nearest step above requirement |
| Backup schedule decided | Backups must be configured at creation or after | Assess RPO requirements |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — File system type selection

| Feature | FSx for Windows | FSx for Lustre | FSx for ONTAP | FSx for OpenZFS |
|---|---|---|---|---|
| Protocol | SMB/CIFS | POSIX (NFS optional) | NFS, SMB, iSCSI | NFS |
| AD integration | Required | Not required | Optional | Not required |
| Multi-AZ | Supported | N/A (PERSISTENT/SCRATCH) | Supported | Not supported |
| Storage type | SSD, HDD | SSD, HDD | SSD, HDD (cache+capacity) | SSD |
| Dedup | Supported | Not supported | Supported | Supported |
| S3 export | Not supported | Supported | Not supported | Not supported |
| Snapshots/shadow copies | Shadow copies | Snapshots | Snapshots | Snapshots |
| Best for | Windows file shares, user home dirs | HPC, ML training | Multi-protocol enterprise | ZFS workloads, NFS |

**Decision logic:**
- Windows file shares, user home directories → FSx for Windows
- HPC, ML, burst compute with S3 data → FSx for Lustre
- Multi-protocol (NFS + SMB + iSCSI), enterprise features → FSx for ONTAP
- NFS with ZFS features (snapshots, compression) → FSx for OpenZFS

## Step 2 — Storage type and throughput capacity

| Type | Storage | Throughput steps | Best for |
|---|---|---|---|
| Windows | SSD | 8-2048 MB/s | Latency-sensitive workloads |
| Windows | HDD | 8-2048 MB/s | Cost-optimized, throughput workloads |
| Lustre | SSD | 125-1000 MB/s/TB | IOPS-intensive HPC |
| Lustre | HDD | 50-200 MB/s/TB | Throughput-intensive HPC |
| ONTAP | SSD/HDD | Tiered (cache + capacity) | Flexible tiering |
| OpenZFS | SSD | Fixed per config | ZFS workloads |

**Throughput CAN be changed after creation** (for most types), but
the change requires a brief I/O suspension. Select the nearest step
above the workload requirement with 20-30% headroom.

## Step 3 — Deployment type (Multi-AZ vs Single-AZ)

| Feature | Multi-AZ | Single-AZ |
|---|---|---|
| Failover | Automatic (standby in different AZ) | None (recovery from backup) |
| RPO | Near-zero | Last backup (minutes-hours) |
| RTO | Sub-minute (Windows), transparent (ONTAP) | Restore time |
| Cost | ~2x Single-AZ | 1x |
| Supported types | Windows, ONTAP | Windows, Lustre (SCRATCH/PERSISTENT), ONTAP, OpenZFS |
| Changeable | CANNOT change after creation | CANNOT change after creation |

**Multi-AZ requires 2 subnets in different AZs.**

```bash
# Create a Multi-AZ Windows file system
aws fsx create-file-system \
  --file-system-type WINDOWS \
  --storage-capacity 1024 \
  --storage-type SSD \
  --windows-configuration \
    DeploymentType=MULTI_AZ_1,ThroughputCapacity=32,\
PreferredSubnetId=subnet-aaa111,PreferredFileServerIp=10.0.1.10 \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --region us-east-1
```

## Step 4 — AD integration and DNS aliases (Windows)

FSx for Windows requires an Active Directory for authentication.

```bash
# Create a Windows file system joined to Managed AD
aws fsx create-file-system \
  --file-system-type WINDOWS \
  --storage-capacity 1024 \
  --storage-type SSD \
  --windows-configuration \
    DeploymentType=MULTI_AZ_1,ThroughputCapacity=32,\
ActiveDirectoryId=d-aaa111222,\
PreferredSubnetId=subnet-aaa111,PreferredFileServerIp=10.0.1.10 \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --region us-east-1
```

**DNS aliases** allow accessing the file system by a custom DNS name
instead of the generated AWS name:

```bash
# Associate a DNS alias
aws fsx associate-file-system-aliases \
  --file-system-id fs-aaa111222 \
  --aliases ["fileshare.example.com"] \
  --region us-east-1
```

## Step 5 — S3 export for Lustre

S3-linked Lustre file systems import data from S3 and export writes
back to S3.

```bash
# Create an S3-linked Lustre file system
aws fsx create-file-system \
  --file-system-type LUSTRE \
  --storage-capacity 1200 \
  --lustre-configuration \
    DeploymentType=PERSISTENT_1,DataCompressionType=LZ4,\
DataRepositoryConfiguration={ImportPath=s3://my-hpc-bucket/data,\
ExportPath=s3://my-hpc-bucket/export,AutoImportPolicy=NEW_CHANGED} \
  --subnet-ids subnet-aaa111 \
  --region us-east-1
```

**Export data back to S3:**

```bash
# Trigger an export task
aws fsx create-data-repository-task \
  --type EXPORT_TO_REPOSITORY \
  --file-system-id fs-aaa111222 \
  --paths ["/data/results"] \
  --report Format=REPORT_CSV,Scope=FAILED_FILES_ONLY,\
Enabled=true,Path=s3://my-hpc-bucket/reports \
  --region us-east-1
```

**Constraint:** S3 bucket must be in the SAME region as the file
system.

## Step 6 — Dedup, shadow copies, and data management

**Dedup (Windows):**

```bash
# Update dedup configuration (via describe/update)
# Dedup is configured at creation or via Windows PowerShell on the file system
# Type: GeneralPurpose (default) or HyperV
```

Dedup savings estimate: 50-80% for file shares, 30-70% for software
shares, near 0% for unique binary data.

**Shadow copies (Windows):** VSS-based point-in-time snapshots for
end-user file recovery. Configured at creation via
`--windows-configuration DailyAutomaticBackupStartTime` and
`AutomaticBackupRetentionDays`.

## Step 7 — KMS encryption

```bash
# Create a file system with a customer-managed KMS key
aws fsx create-file-system \
  --file-system-type WINDOWS \
  --storage-capacity 1024 \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/xxx \
  --windows-configuration DeploymentType=MULTI_AZ_1,ThroughputCapacity=32 \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --region us-east-1
```

**KMS key CANNOT be changed after creation.** Choose customer-
managed for audit/control or AWS-managed (default) for simplicity.

## Step 8 — Backup and restore

```bash
# Create a manual backup
aws fsx create-backup \
  --file-system-id fs-aaa111222 \
  --tags Key=Name,Value=pre-change-backup \
  --region us-east-1

# Restore from a backup (creates a NEW file system)
aws fsx create-file-system-from-backup \
  --backup-id backup-xxx \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --region us-east-1

# List backups
aws fsx describe-backups \
  --filters Name=file-system-id,Values=fs-aaa111222 \
  --region us-east-1 --output table
```

**Constraints:** Restore creates a NEW file system (the original is
not overwritten). Automated backups are configured at creation.

## Step 9 — ONTAP SVM and volume tiering

FSx for ONTAP uses Storage Virtual Machines (SVMs) and volumes with
tiering (SSD cache + HDD capacity pool).

```bash
# Create an ONTAP file system
aws fsx create-file-system \
  --file-system-type ONTAP \
  --storage-capacity 1024 \
  --ontap-configuration DeploymentType=MULTI_AZ_1,\
PreferredSubnetId=subnet-aaa111 \
  --subnet-ids subnet-aaa111 subnet-bbb222 \
  --region us-east-1

# Create an SVM (after file system is ACTIVE)
aws fsx create-storage-virtual-machine \
  --file-system-id fs-aaa111222 \
  --name svm-prod \
  --region us-east-1

# Create a volume with tiering
aws fsx create-volume \
  --volume-type ONTAP \
  --name vol-prod \
  --ontap-configuration \
    JunctionPath=/vol-prod,SizeInMegabytes=1048576,\
StorageEfficiency=enabled,TieringPolicy=auto,\
StorageVirtualMachineId=svm-xxx \
  --region us-east-1
```

## Step 10 — Maintenance windows

FSx performs maintenance (patches, updates) during a configurable
maintenance window.

```bash
# Configure the maintenance window
aws fsx update-file-system \
  --file-system-id fs-aaa111222 \
  --windows-configuration \
    WeeklyMaintenanceStartTime=2:01:00 \
  --region us-east-1
# Format: DayOfWeek:Hour:Minute (Day: 1=Mon ... 7=Sun)
```

**During maintenance:** the file system may briefly be unavailable
(Single-AZ) or fail over to the standby (Multi-AZ). Schedule during
off-peak hours.

## Step 11 — Recent features

- **FSx for OpenZFS (2023-2024):** ZFS-based file system with
  snapshots, compression, and NFS. Added for workloads needing ZFS
  features without managing ZFS infrastructure.

- **Lustre PERSISTENT_2 with SSD metadata (2024-2025):** Enhanced
  PERSISTENT_2 deployment with SSD-backed metadata configuration for
  workloads with many small files.

- **Data compression for Lustre (2024-2025):** LZ4 compression for
  Lustre file systems, reducing storage footprint by 30-60% for
  compressible data.

- **ONTAP volume tiering improvements (2024-2025):** Enhanced
  auto-tiering policies with configurable cooling period and
  improved capacity pool performance.

- **Multi-AZ for ONTAP (2024-2025):** Multi-AZ deployment for FSx
  for ONTAP, providing transparent failover for multi-protocol
  workloads.

- **FSx backup cross-region copy (2025-2026):** Cross-region backup
  copy for DR, enabling FSx backups to be copied to a different
  region for cross-region recovery.

## NEVER do these things

1. **NEVER choose Single-AZ for production workloads requiring high
   availability.** Multi-AZ provides automatic failover; Single-AZ
   does not. Multi-AZ CANNOT be changed to Single-AZ after creation.

2. **NEVER pick an arbitrary throughput capacity value.** Throughput
   is stepped. Pick the nearest step above the workload requirement
   with 20-30% headroom. An invalid step will cause a creation error.

3. **NEVER assume S3 export means data lives in S3.** S3 export
   creates a LINK. Data is stored on the Lustre file system's
   SSD/HDD. S3 is the backing repository for import/export.

4. **NEVER create a Windows file system without AD integration.**
   FSx for Windows REQUIRES Active Directory. Ensure the directory
   is ACTIVE before creating the file system.

5. **NEVER forget the KMS key cannot be changed after creation.**
   Choose customer-managed key for audit/control requirements up
   front. Changing encryption requires recreating the file system.

6. **NEVER use SCRATCH Lustre for durable workloads.** SCRATCH file
   systems are ephemeral — data is lost on deletion. Use PERSISTENT
   for durable workloads that need data to survive server failures.

7. **NEVER assume dedup savings are the same for all workloads.**
   Dedup savings depend on data patterns (50-80% for file shares,
   near 0% for unique binary data). Estimate before enabling.

8. **NEVER create an ONTAP volume without configuring tiering.**
   Without tiering, all data stays on the SSD cache tier (most
   expensive). Configure auto-tiering to move cold data to the HDD
   capacity pool.

9. **NEVER restore a backup expecting it to overwrite the original.**
   Restore creates a NEW file system from the backup. The original
   file system is not affected. Plan for a DNS alias or mount-point
   change.

10. **NEVER forget the maintenance window.** FSx performs patches
    during the maintenance window. Schedule it during off-peak hours
    to minimize impact.

## Output format

```text
FSX_FILESYSTEM: <file-system-id> (<type>, <deployment-type>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] File system type: Windows | Lustre | ONTAP | OpenZFS
  [✓|✗] Storage type: SSD | HDD
  [✓|✗] Storage capacity: <GB>
  [✓|✗] Deployment type: Multi-AZ | Single-AZ | SCRATCH | PERSISTENT
  [✓|✗] Throughput capacity: <MB/s or MB/s per TB>
  [✓|✗] VPC: <vpc-id>
  [✓|✗] Subnet AZ1: <subnet-id> (<az>)
  [✓|✗] Subnet AZ2: <subnet-id> (<az>) — required for Multi-AZ
  [✓|✗] AD integration: <directory-id> — joined | not needed
  [✓|✗] DNS aliases: <alias list> | none
  [✓|✗] S3 export (Lustre): s3://<bucket> (import/export configured) | not applicable
  [✓|✗] Dedup: enabled (<type>, est. savings <n>%) | disabled
  [✓|✗] Shadow copies (Windows): enabled | disabled | not applicable
  [✓|✗] KMS encryption: <key-id> (customer-managed) | AWS-managed
  [✓|✗] Backup: automatic (daily, retention <days>) + manual
  [✓|✗] ONTAP tiering: auto (cooling period <days>) | not applicable
  [✓|✗] Maintenance window: <day>:<hour>:<minute>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws fsx describe-file-systems --file-system-ids <file-system-id> --region <region>
  aws fsx describe-backups --filters Name=file-system-id,Values=<file-system-id> --region <region>
```

### Worked example — FSx for Windows Multi-AZ with AD and dedup

```text
FSX_FILESYSTEM: fs-aaa111222 (WINDOWS, MULTI_AZ_1)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] File system type: Windows
  [✓] Storage type: SSD
  [✓] Storage capacity: 1024 GB
  [✓] Deployment type: Multi-AZ
  [✓] Throughput capacity: 32 MB/s
  [✓] VPC: vpc-aaa11122
  [✓] Subnet AZ1: subnet-aaa111 (us-east-1a)
  [✓] Subnet AZ2: subnet-bbb222 (us-east-1b)
  [✓] AD integration: d-aaa111222 — joined
  [✓] DNS aliases: fileshare.example.com
  [✓] Dedup: enabled (GeneralPurpose, est. savings 60%)
  [✓] Shadow copies: enabled
  [✓] KMS encryption: AWS-managed
  [✓] Backup: automatic (daily, retention 7 days)
  [✓] Maintenance window: 2:01:00 (Tuesday 01:00)
  [✓] Tags: Environment=production, ManagedBy=cloudops
VERIFICATION_COMMANDS:
  aws fsx describe-file-systems --file-system-ids fs-aaa111222 --region us-east-1
  aws fsx describe-backups --filters Name=file-system-id,Values=fs-aaa111222 --region us-east-1
```

## Error handling

### File system stuck in CREATING state
- File system creation can take 10-60 minutes depending on type and
  size. If it stays in CREATING beyond expected time, check subnet
  configuration, AD integration (for Windows), and IAM permissions.

### AD domain join failure (Windows)
- The directory may not be ACTIVE, or the security group may block
  required AD ports (53, 88, 389, 445). Verify the directory status
  and security group rules.

### S3 export/import not working (Lustre)
- The S3 bucket may not exist, or the IAM permissions may be
  incorrect. Verify the bucket is in the same region and the FSx
  service role has read/write access to the bucket.

### Multi-AZ failover not working
- The standby may not be in a different AZ, or the security group
  may block inter-AZ traffic. Verify both subnets are in different
  AZs and the security group allows traffic on required ports.

### Throughput capacity change failed
- The new throughput value may not be a valid step, or a maintenance
  window is required. Verify the throughput step is valid and
  schedule the change during a maintenance window.

## Domain

AWS CloudOps / Amazon FSx File System Provisioning & Storage
Management.

## AWS documentation

- **Amazon FSx** — https://docs.aws.amazon.com/fsx/latest/GettingStartedGuide/what-is-fsx.html
- **FSx for Windows** — https://docs.aws.amazon.com/fsx/latest/WindowsGuide/what-is-fsxw.html
- **FSx for Lustre** — https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is-fsx-lustre.html
- **FSx for ONTAP** — https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/what-is-fsx-ontap.html
- **FSx for OpenZFS** — https://docs.aws.amazon.com/fsx/latest/OpenZFSGuide/what-is-fsx-openzfs.html
- **Multi-AZ deployment** — https://docs.aws.amazon.com/fsx/latest/WindowsGuide/high-availability-multiAZ.html
- **S3 data repository (Lustre)** — https://docs.aws.amazon.com/fsx/latest/LustreGuide/create-data-repository-association.html
- **Backups** — https://docs.aws.amazon.com/fsx/latest/WindowsGuide/using-backups.html
- **Dedup** — https://docs.aws.amazon.com/fsx/latest/WindowsGuide/data-dedup.html
- **KMS encryption** — https://docs.aws.amazon.com/fsx/latest/WindowsGuide/encryption-at-rest.html
