# Advanced Patterns — FSx Filesystem Deployer

Expert-knowledge deep dives, edge-case catalogs, and recent AWS features moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Expert heuristic: Multi-AZ vs Single-AZ failover pairing (moved from SKILL.md)

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

## Expert heuristic: throughput capacity step sizing (moved from SKILL.md)

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

## Expert heuristic: S3 export for Lustre (moved from SKILL.md)

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

## Expert heuristic: dedup savings estimation (moved from SKILL.md)

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

## Step 11 — Recent features (moved from SKILL.md)

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

