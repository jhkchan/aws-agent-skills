# Cache and Upload Buffer Sizing — Storage Gateway Deployer

Deep reference on local disk allocation for Storage Gateway: cache
sizing (S3 File Gateway, Volume Gateway cached mode), upload buffer
sizing (all gateway types), Volume Gateway stored mode (no cache),
and performance isolation between cache and buffer. Loaded on demand
by the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Cache fundamentals

### What the cache does

The cache stores recently accessed data locally for low-latency reads.
When a client reads a file (S3 File Gateway) or block (Volume Gateway
cached), the gateway checks the cache first:

```text
Read request → cache hit (low latency, local) → return data
Read request → cache miss → fetch from S3/EBS → store in cache → return data
```

The cache hit ratio (CacheHitPercent in CloudWatch) determines read
performance. A high ratio means most reads are served locally; a low
ratio means most reads require an S3/EBS fetch over the network.

### Cache sizing rules

| Workload type | Recommended cache size | Rationale |
|---|---|---|
| Active file share (hot data) | 10-20% of total dataset | Working set fits in cache; most reads are local |
| Archive/backup (cold data) | 5-10% of total dataset | Mostly sequential writes; minimal read-back |
| Database on Volume Gateway cached | 20-30% of dataset | High random read I/O; needs larger cache |
| Mixed workload | 15% of dataset + 100 GB buffer | Balance between hot and cold access patterns |

**Hard minimum:** 150 GB for all gateway types that use cache.

**Sizing formula:**
```text
Cache (GB) = max(150, Working_Set_Size_GB × 1.2)
  where Working_Set_Size_GB ≈ Total_Dataset_GB × Hot_Data_Percentage
  Hot_Data_Percentage: 10-30% depending on workload
```

### When to expand the cache

Monitor `CacheHitPercent` and `CachePercentUsed` in CloudWatch:

- `CacheHitPercent` < 80% → cache too small for the working set.
  Add more cache capacity.
- `CachePercentUsed` > 90% → cache nearly full. Add capacity before
  it reaches 100% (which forces evictions and lowers hit ratio).
- `CacheHitPercent` trending down over time → dataset growing, working
  set expanding. Add cache proactively.

## Upload buffer fundamentals

### What the upload buffer does

The upload buffer queues data that has been written locally but not
yet uploaded to AWS. Writes go to the buffer first, then the gateway
asynchronously uploads to S3/EBS.

```text
Write request → write to upload buffer (low latency, local)
  → gateway async uploads buffer → S3/EBS (background)
  → buffer space freed for new writes
```

If the upload buffer fills up, new writes BLOCK until the gateway
uploads enough data to free space. This causes application-level
stalls.

### Upload buffer sizing rules

| Workload type | Recommended buffer size | Rationale |
|---|---|---|
| Low write rate (< 10 GB/day) | 150 GB (minimum) | Small buffer is sufficient; uploads keep up |
| Medium write rate (10-100 GB/day) | 150-300 GB | Buffer absorbs daily change rate with headroom |
| High write rate (> 100 GB/day) | 1.5x daily change rate | Large buffer prevents write stalls during peak |
| Bulk migration (initial load) | 500 GB+ | Large initial writes need a big buffer |

**Hard minimum:** 150 GB for all gateway types.

**Sizing formula:**
```text
Upload_Buffer (GB) = max(150, Daily_Change_Rate_GB × 1.5)
  where Daily_Change_Rate_GB = estimated data written per day
```

### When to expand the upload buffer

Monitor `UploadBufferPercentUsed` in CloudWatch:

- `UploadBufferPercentUsed` > 80% → buffer is filling faster than
  uploads can drain it. Add more buffer.
- Write latency spikes during peak hours → buffer is full and writes
  are blocking. Add buffer or increase bandwidth rate limit.
- `UploadBufferPercentUsed` sustained at 100% → critical; writes are
  blocked. Add buffer immediately.

## Volume Gateway stored mode — no cache

Volume Gateway stored mode uses the local disk as the PRIMARY copy
of the data. There is NO cache in stored mode — the entire dataset
lives locally, and the upload buffer asynchronously replicates to
AWS for backup.

```text
Stored mode architecture:
  Local disk (primary) ← application reads/writes directly
  Upload buffer → async replicates to EBS snapshots (AWS cloud backup)

  NO cache needed — local disk IS the primary storage
  Upload buffer IS needed — for async replication to AWS
```

**Stored mode disk sizing:**
```text
Local disk (GB) = Total_Dataset_GB + Upload_Buffer_GB
  where Upload_Buffer_GB = max(150, Daily_Change_Rate_GB × 1.5)
```

## Performance isolation: separate physical disks

Always use SEPARATE physical disks for cache and upload buffer.

| Configuration | Cache I/O pattern | Buffer I/O pattern | Risk if combined |
|---|---|---|---|
| Separate disks | Random reads (hot data) | Sequential writes (upload queue) | No contention; optimal |
| Same disk | Mixed random + sequential | Mixed random + sequential | I/O contention; degraded performance for both |
| Same disk (SSD) | Mixed | Mixed | Acceptable for small deployments; suboptimal for production |

**Recommendation:** allocate cache and upload buffer on different
physical disks (or different LUNs on a SAN) for production deployments.

## Terraform examples

```hcl
# Gateway activation
resource "aws_storagegateway_gateway" "main" {
  gateway_ip_address = "192.168.1.50"
  gateway_name       = "prod-s3-file-gateway"
  gateway_timezone   = "GMT-5:00"
  gateway_type       = "FILE_S3"

  tags = {
    Environment = "production"
  }
}

# Cache disk allocation
resource "aws_storagegateway_cache" "cache" {
  gateway_arn = aws_storagegateway_gateway.main.gateway_arn
  disk_id     = data.aws_storagegateway_local_disk.cache.disk_id
}

# Upload buffer allocation
resource "aws_storagegateway_upload_buffer" "buffer" {
  gateway_arn = aws_storagegateway_gateway.main.gateway_arn
  disk_id     = data.aws_storagegateway_local_disk.buffer.disk_id
}
```

## Expert heuristic: cache vs upload buffer sizing (moved from SKILL.md)

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

## Critical sizing rules (moved from SKILL.md)

**Critical sizing rules:**
- Cache: 150 GB minimum; size for the working set of hot data (10-20%
  of total dataset for active workloads).
- Upload buffer: 150 GB minimum; size for 1.5x the estimated daily data
  change rate.
- Volume Gateway stored mode: NO cache needed (local disk is primary).
- Use separate physical disks for cache and upload buffer for
  performance isolation.
