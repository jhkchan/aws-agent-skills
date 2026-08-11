# Deployment Types & AD Integration

## FSx for Windows File Server

### Deployment Types
| Type | Availability | Use Case |
|---|---|---|
| Multi-AZ | 99.99% SLA | Production, failover-ready |
| Single-AZ | 99.9% SLA | Dev/test, cost-sensitive |

### Storage Types
- SSD: For latency-sensitive workloads (databases, home directories)
- HDD: For archive, bulk file storage (lower cost)

### Throughput Capacity
- Measured in MB/s, independent of storage capacity
- Steps: 8, 16, 32, 64, 128, 256, 512, 1024, 2048 MB/s
- Must be sized based on concurrent user count and workload

### AD Integration
1. **AWS Managed Microsoft AD**: Full AWS-managed AD in your VPC
2. **Self-Managed AD**: Your own AD via forest trust or direct join
3. **AD Connector**: Routes to existing on-prem AD (no caching)

### Key Features
- Data deduplication (saves up to 80% for general-purpose file shares)
- Shadow copies (VSS-based point-in-time recovery)
- Automatic backups (daily, configurable retention)
- DNS aliases (for seamless failover)

## FSx for Lustre

### Deployment Types
| Type | Persistence | Use Case |
|---|---|---|
| PERSISTENT_1 | Durable | Long-term HPC, ML training |
| PERSISTENT_2 | Durable, higher performance | Latest HPC workloads |
| SCRATCH_1 | Ephemeral | Burst HPC, cost-sensitive |
| SCRATCH_2 | Ephemeral, higher performance | Short bursty HPC |

### S3 Integration
- Import data from S3 (linked bucket)
- Export results back to S3
- Lazy loading with metadata prefetch
- Auto-export on write

## FSx for NetApp ONTAP
- Storage Virtual Machines (SVMs) for multi-protocol access
- Volume tiering: move cold data to capacity pool
- Snapshots, SnapMirror replication
- Multi-protocol: NFS, SMB, iSCSI

## FSx for OpenZFS
- ZFS features: snapshots, clones, compression
- NFS access
- Intelligent tiering
