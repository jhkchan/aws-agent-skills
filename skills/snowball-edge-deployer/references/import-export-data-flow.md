# Import and Export Data Flow — Snowball Edge Deployer

Deep reference on the full data lifecycle for import jobs (on-premises
→ S3 via device), export jobs (S3 → on-premises via device), NFS and
S3 adapter transfer interfaces, data validation reports, and return
shipping logistics. Loaded on demand by the skill — kept out of the
main SKILL.md body so the provisioning procedure stays scannable.

## Import job data flow

### Full lifecycle

```text
Phase 1: Job creation
  aws snowball create-job --job-type IMPORT ...
  → AWS prepares the device with the job configuration
  → AWS ships the device to the provided address

Phase 2: Device receipt and setup
  → Receive device (2-7 business days)
  → Power on, connect to network
  → Download manifest from AWS console
  → Pair device: snowballEdge configure-device ...
  → Unlock device: snowballEdge unlock-device ...

Phase 3: Data transfer
  → Start NFS: snowballEdge start-service --service-id nfs ...
  → Mount NFS: mount -t nfs <device-ip>:/nfs/path /mnt/snowball
  → Copy data: cp -r /data/* /mnt/snowball/
  → OR use S3 adapter: aws s3 cp /data/ s3://bucket/ --endpoint ...

Phase 4: Return and upload
  → Stop NFS: snowballEdge stop-service --service-id nfs ...
  → Power off device
  → Attach AWS-provided shipping return label
  → Ship device back to AWS

Phase 5: AWS processing
  → AWS receives device
  → AWS uploads data to the specified S3 bucket (hours to days)
  → Data validation report available in AWS console
  → AWS securely erases the device
```

### Key insight: data does NOT upload in real-time

The device is a physical data shuttle. It does NOT have internet
connectivity to upload data to S3 while at the customer site. Data
is uploaded ONLY after the device is returned to AWS.

This is the #1 misunderstanding that leads to "where is my data in
S3?" support tickets.

## Export job data flow

### Full lifecycle

```text
Phase 1: Job creation
  aws snowball create-job --job-type EXPORT ...
  → AWS reads data from the specified S3 bucket
  → AWS pre-loads the data onto the device
  → AWS ships the device to the provided address

Phase 2: Device receipt
  → Receive device (2-7 business days)
  → Power on, connect to network
  → Pair and unlock device (same as import)

Phase 3: Data offload
  → Start NFS interface
  → Mount NFS and copy data off the device
  → OR use S3 adapter to read data

Phase 4: Return
  → Power off device
  → Return to AWS using provided shipping label
  → AWS securely erases the device
```

### Export limitations

- One S3 bucket per export job. For multiple buckets, create separate
  jobs.
- Export data is a point-in-time snapshot at job creation time. S3
  objects added after job creation are NOT included.
- Total export size must fit on the device (210 TB max for Storage
  Optimized).

## NFS interface

### Start NFS service

```bash
snowballEdge start-service \
  --service-id nfs \
  --device-ip-address 192.168.1.100 \
  --manifest-file manifest.bin \
  --unlock-code ABCD-1234-WXYZ-5678 \
  --endpoint https://192.168.1.100:9091
```

### Get NFS connection details

```bash
snowballEdge describe-service \
  --service-id nfs \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091
# Returns: NFS IP addresses and mount paths
```

### Mount and transfer

```bash
# Mount the NFS share
mount -t nfs -o nolock,hard 192.168.1.100:/nfs/path /mnt/snowball

# Parallel copy for large datasets
find /data -type f | xargs -P 16 -I{} cp {} /mnt/snowball/

# Verify transfer
du -sh /mnt/snowball/
du -sh /data/
# Both should match (approximately)
```

### NFS performance expectations

| Network link | Expected throughput | 210 TB transfer time |
|---|---|---|
| 1 GbE | ~100 MB/s | ~25 days |
| 10 GbE | ~400 MB/s | ~6 days |
| 25 GbE | ~700 MB/s | ~3.5 days |
| 40 GbE | ~900 MB/s | ~2.7 days |
| 100 GbE | ~1 GB/s | ~2.4 days |

## S3 adapter interface

### Use aws s3 cp with the device endpoint

```bash
# Configure the S3 adapter endpoint
aws configure set default.s3.endpoint http://192.168.1.100:8080

# Copy data with high parallelism
aws s3 cp /data/ s3://snowball-bucket/ \
  --endpoint http://192.168.1.100:8080 \
  --recursive \
  --max-concurrent-requests 32

# Or sync for incremental updates
aws s3 sync /data/ s3://snowball-bucket/ \
  --endpoint http://192.168.1.100:8080
```

### S3 adapter vs NFS

| Feature | NFS | S3 adapter |
|---|---|---|
| Best for | Large files, sequential access | Many small files, parallel transfer |
| Throughput | 400-800 Mbps | 200-500 Mbps |
| Parallelism | Via xargs -P | Via --max-concurrent-requests |
| File size handling | Optimized for > 100 GB | Optimized for < 100 MB |
| Ease of use | mount + standard file ops | aws s3 cp syntax |

## Data validation report

After AWS processes the returned import device, a validation report
is available:

```bash
# Check job completion and report availability
aws snowball describe-job \
  --job-id $JOB_ID \
  --region us-east-1 \
  --query 'JobMetadata.{JobState:JobState,JobLogInfo:JobLogInfo}'
```

### Report contents

- Total objects transferred successfully.
- Total objects that failed (with error details per object).
- Total data transferred (bytes).
- Transfer start and end timestamps.
- Downloadable CSV summary for audit/compliance.

### Handling failed objects

Objects may fail due to:
- S3 bucket permissions (IAM role lacks PutObject).
- Object key naming issues (special characters, length).
- S3 bucket storage quota (rare).

Re-transfer failed objects by:
1. Create a new import job.
2. Copy only the failed objects to the new device.
3. Return the device for processing.

## Return shipping logistics

- AWS provides a return shipping label (e-ink on the device or
  printable from the console).
- The return label is pre-paid; no additional shipping cost.
- Return the device in the original packaging.
- AWS tracks the return shipment; status visible in the console.
- AWS securely erases the device after data upload (NIST 800-88).

## Terraform example

```hcl
resource "aws_snowball_job" "import" {
  address_id   = aws_snowball_address.main.id
  description  = "Data migration to S3"
  job_type     = "IMPORT"
  snowball_type = "EDGE_STORAGE_OPTIMIZED"
  shipping_option = "NEXT_DAY"

  resources {
    s3_resources {
      bucket_arn = "arn:aws:s3:::my-migration-bucket"
    }
  }

  notification {
    job_state_changes_only = true
    notify_all = false
  }

  tags = {
    Environment = "migration"
    Project     = "data-lift"
  }
}
```

## Expert heuristic: import job data flow (device → S3 bucket)

A baseline model says "create a job and copy data." The correct
heuristic recognizes the full lifecycle: create job → receive device →
unlock → start NFS → copy data → return device → AWS uploads → validate.

```text
Import job data flow:
  1. Create import job (specify S3 destination bucket)
     → AWS prepares and ships the device
  2. Receive device (2-7 business days)
     → Power on, connect to network
  3. Pair device (download manifest from AWS console)
     → Apply manifest via snowballEdge CLI
  4. Unlock device (using unlock code from AWS console)
     → snowballEdge unlock-device --endpoint ...
  5. Start NFS interface
     → snowballEdge start-service --service-id nfs-1 ...
  6. Mount NFS and copy data (or use aws s3 cp via S3 adapter)
     → mount -t nfs <device-ip>:/nfs/path /mnt/snowball
     → cp -r /data/* /mnt/snowball/
     → OR: aws s3 cp /data/ s3://snowball-bucket/ --endpoint ...
  7. Stop NFS, power off device
  8. Return device (AWS-provided shipping label)
  9. AWS receives device → uploads data to S3 (hours to days)
  10. Data validation report available in AWS console
```

**Key implication:** the #1 cause of "where is my data in S3?" is
expecting the device to upload in real-time. The device is a physical
shuttle — data uploads only AFTER the device is returned and processed
by AWS.

## Expert heuristic: NFS transfer via smbclient/aws s3 cp parallelism

Data transfer speed depends on the interface (NFS vs S3 adapter) and
the number of parallel threads. NFS is generally faster for large
files; the S3 adapter supports aws s3 cp with parallelism.

```text
Transfer optimization:
  NFS (large files, sequential):
    ├── mount -t nfs <device-ip>:/nfs/path /mnt/snowball
    ├── Use parallel copy: find /data -type f | xargs -P 16 -I{} cp {} /mnt/snowball/
    └── Expected: 400-800 Mbps per NFS connection

  S3 adapter (many small files, aws s3 cp):
    ├── aws s3 cp /data/ s3://snowball-bucket/ --endpoint http://<device-ip>:8080 --recursive
    ├── Increase parallelism: --max-concurrent-requests 32 (default 5)
    └── Expected: 200-500 Mbps with high parallelism

  Rule of thumb:
    ├── > 100 GB files → NFS (single large sequential copy)
    ├── < 100 MB files → S3 adapter with --max-concurrent-requests 32
    └── Mixed → NFS with parallel copy threads
```
