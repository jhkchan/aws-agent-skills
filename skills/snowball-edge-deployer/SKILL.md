---
name: snowball-edge-deployer
description: 'Deploys AWS Snowball Edge with production defaults: job creation (import vs export), device type selection (Storage Optimized, Compute Optimized, Snowcone), S3 bucket configuration for import/export, Lambda functions for compute, NFS interface for data transfer, IoT certificate for device pairing, shipping and tracking, data transfer reporting, cluster mode (5-10 nodes for compute), device unlock, return shipping, data validation report, EKS Anywhere on Snowball, and long-term rental. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Snowball Edge job, setting up a data migration device, configuring cluster mode, deploying EKS Anywhere, or transferring bulk data. Triggers: create snowball job, snowball edge import, snowball edge export, snowball device unlock, snowball cluster mode, snowball nfs transfer, eks anywhere snowball, snowcone deploy, snowball data migration.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with snowball and s3 access. Works with Terraform aws_snowball_job resources and CloudFormation AWS::Snowball::Job templates. Requires the snowballEdge client (opnix) on the receiving device for unlock and data transfer.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Migration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, snowball-edge, snowball, snowcone, cloudops, deploy, migration, provisioning, data-transfer, cluster-mode, eks-anywhere
  dependencies: aws-orchestrator
  keywords: aws, snowball edge, snowball, snowcone, data migration, bulk transfer, cloudops, deploy, provisioning, import job, export job, cluster mode, eks anywhere, nfs, lambda, device unlock, iot certificate
  when_to_use: Invoke when the user wants to create an AWS Snowball Edge job (import or export), select a device type (Storage Optimized, Compute Optimized, Snowcone), configure S3 buckets for data transfer, set up NFS for data transfer, unlock a Snowball device, configure cluster mode for compute resiliency, deploy Lambda functions on Snowball, set up EKS Anywhere on Snowball, or manage long-term rental. Do NOT invoke for AWS DataSync (use datasync skills), AWS Transfer Family (SFTP), or online S3 replication (use S3 Cross-Region Replication).
---

# Snowball Edge Deployer

An AWS CloudOps agent skill that deploys AWS Snowball Edge with correct
production defaults. The skill walks the operator through job creation
(import vs export), device type selection (Storage Optimized, Compute
Optimized, Snowcone), S3 bucket configuration, Lambda function
deployment for compute, NFS interface for data transfer, IoT
certificate for device pairing, shipping and tracking, cluster mode
configuration, device unlock, return shipping, and data validation.
It captures the migration topology, explains why each default matters,
and emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create Snowball job, Snowball Edge import, Snowball Edge export,
Snowball device unlock, Snowball cluster mode, Snowball NFS transfer,
Snowcone deploy, EKS Anywhere Snowball, Snowball data migration,
Snowball Lambda compute, Snowball Edge long-term rental.

## STRICT output contract

When this skill is invoked with a Snowball Edge deployment request
(create a job, configure data transfer, set up cluster mode, unlock a
device, or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `SNOWBALL_EDGE:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Job type selection (import vs export) | Core decision |
| Step 2 — Device type selection | Hardware choice |
| Step 3 — S3 bucket configuration | Data source/destination |
| Step 4 — Device pairing and unlock | Physical setup |
| Step 5 — NFS interface for data transfer | Bulk data copy |
| Step 6 — Lambda functions for compute | Edge compute |
| Step 7 — Cluster mode (5-10 nodes) | Compute resiliency |
| Step 8 — Shipping, tracking, and return | Logistics |
| Step 9 — Data validation and reporting | Transfer verification |
| Step 10 — EKS Anywhere and long-term rental | Advanced use cases |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/import-export-data-flow.md | Data flow detail |
| references/cluster-and-compute.md | Cluster + compute detail |

## Mindset

**One-line takeaway:** Snowball Edge is a physical data transfer and
edge computing device shipped by AWS. Import jobs move data FROM
on-premises TO S3 (device → S3). Export jobs move data FROM S3 TO
on-premises (S3 → device). Cluster mode connects 5-10 devices for
compute resiliency. The device must be unlocked with its credentials
before any data transfer or compute.

Three misconceptions dominate Snowball Edge misdesign at provisioning
time:

- **"The device uploads data to S3 automatically after I copy files
  to it."** It does NOT — for import jobs, you copy data to the device
  via NFS (or aws s3 cp), then physically RETURN the device. AWS
  uploads the data to S3 after receiving the device back. The device
  is NOT an internet-connected gateway; it is a suitcase-sized data
  shuttle. This misunderstanding leads operators to wait for an upload
  that never starts.

- **"Any device type works for any workload."** Device types have
  distinct capabilities. Storage Optimized (80 TB or 210 TB usable)
  is for pure data migration. Compute Optimized adds an AMI and Lambda
  for edge processing. Snowcone (8 TB usable, 2.1 kg) is for smaller
  transfers and edge computing in space-constrained environments.
  Choosing the wrong device wastes money or limits capability.

- **"Cluster mode is just for extra storage."** Cluster mode connects
  5-10 Storage Optimized or Compute Optimized devices into a single
  logical entity for COMPUTE resiliency (not just more storage). If
  one device fails, the cluster continues operating. This is essential
  for edge computing workloads (IoT processing, ML inference, EKS
  Anywhere) that cannot tolerate downtime.

## Configuration dependency graph (novel heuristic)

Snowball Edge configurations are NOT independent. The job must be
created before the device ships. The device must be unlocked before
data transfer. NFS must be started before copying data. The device
must be returned before AWS imports data to S3. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Job creation | AWS account; shipping address; S3 bucket exists (import: destination; export: source); device type selected; snowball type (device) | job type (IMPORT/EXPORT) and device type are immutable after creation | device shipment |
| Shipping address | valid physical address (no PO boxes for Snowball Edge; PO boxes OK for Snowcone) | AWS ships only to supported regions/countries; remote areas may take longer | device delivery |
| Device delivery | job created; address validated | delivery takes 2-7 business days depending on location | device pairing |
| Device pairing (manifest + unlock code) | device powered on and connected to network; manifest downloaded from AWS console | the manifest is job-specific and CANNOT be reused across jobs | device unlock |
| Device unlock | device paired (manifest applied); unlock code entered via snowballEdge CLI | device CANNOT be used without unlock; wrong manifest = re-pair required | NFS, S3 interface, Lambda |
| NFS interface start | device unlocked | NFS must be started manually via snowballEdge CLI; does not auto-start | NFS data transfer |
| S3 adapter interface | device unlocked | provides an S3-compatible endpoint for aws s3 cp; alternative to NFS | S3 CLI data transfer |
| Data transfer (import) | NFS or S3 interface active | data is stored on device locally; NOT uploaded until device is returned | return shipping |
| Data transfer (export) | device received from AWS; NFS or S3 interface active | export data was pre-loaded by AWS before shipping | on-premises consumption |
| Return shipping (import) | data transfer complete | AWS uploads data to S3 AFTER receiving the device; tracking is available | S3 data import |
| Data validation report | return shipping processed by AWS | report is available in the AWS console after import; shows success/failure per object | transfer verification |
| Lambda functions | device unlocked; Compute Optimized or Snowcone device | Lambda functions are deployed to the device for edge compute | edge processing |
| Cluster mode | 5-10 devices; all same device type; all unlocked; connected on same network | cluster provides compute resiliency; single-node failure does not stop the cluster | resilient edge compute |

**The return-before-upload row is the one a baseline model misses.**
A naive deployment says "copy data to the device." The correct
heuristic recognizes that for import jobs, copying data is only step
one — the device must be physically returned for AWS to process the
upload to S3. The data validation report is only available AFTER the
return. The procedure below forces explicit planning for the full
device lifecycle.

**Cross-dependency gotchas:**
- The manifest is job-specific. Each job has its own manifest and
  unlock code. Reusing a manifest from a different job fails the
  pairing step.
- NFS interface must be started manually after unlock. It does not
  auto-start. Forgetting to start NFS is a common blocker.
- For import jobs, the S3 destination bucket must exist BEFORE job
  creation. AWS validates the bucket at job creation time.
- Cluster mode requires all devices to be on the same network with
  mutual network visibility. Devices on different subnets may not
  form a cluster.
- Export jobs can only export data from one S3 bucket per job. For
  multiple buckets, create multiple export jobs.

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

## Expert heuristic: cluster mode for resiliency

Cluster mode connects 5-10 Snowball Edge devices into a single logical
entity for COMPUTE resiliency (not storage aggregation). If one device
fails, the cluster continues operating.

```text
Cluster mode decision tree:
  ├── Need edge compute with HA? → cluster mode (min 5 nodes)
  │     All nodes same device type, same network
  │     Quorum: 5-node cluster tolerates 2 node failures
  │     Use case: IoT processing, ML inference at edge
  ├── Need just data transfer? → single device (no cluster)
  │     One device, one job, return when done
  ├── Need EKS Anywhere? → cluster mode (5 nodes minimum)
  │     EKS Anywhere requires persistent cluster
  └── Need more than 210 TB transfer? → multiple single-device jobs
        NOT cluster mode (cluster is for compute, not storage pooling)
```

**Key implication:** cluster mode is for compute resiliency, not for
aggregating storage. For large data transfers, use multiple
single-device jobs, not a cluster.

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

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Valid shipping address | AWS ships physical devices; no PO boxes for Snowball Edge | Confirm address in AWS account |
| S3 bucket exists (import: destination; export: source) | Jobs require a bucket before creation | `aws s3api head-bucket --bucket <name>` |
| AWS region supporting Snowball | Not all regions support all device types | Check Snowball availability in target region |
| Data volume estimated | Determines device type and number of jobs | Assess total data size |
| Network port available | Device needs a network connection for unlock and transfer | Confirm available network port (1/10/25/40/100 GbE) |
| snowballEdge CLI installed | Required for device unlock and NFS start | Verify `snowballEdge version` on host machine |
| IAM role/policy for job | AWS needs permissions to read/write the S3 bucket | Verify IAM policy includes snowball:* and s3:* |
| Manifest and unlock code (post-delivery) | Required to pair and unlock the device | Download from AWS Snowball console after job creation |
| Cluster node count (if cluster mode) | Cluster requires 5-10 nodes of same type | Confirm node count and device type |
| Shipping return plan (import) | Device must be returned for AWS to process upload | Ensure return shipping is planned |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Job type selection (import vs export)

Snowball Edge supports two job types. The type is set at job creation
and CANNOT be changed.

| Job type | Data direction | Use case |
|---|---|---|
| Import | On-premises → S3 (via device) | Migrating on-premises data to AWS |
| Export | S3 → On-premises (via device) | Distributing AWS data to on-premises / offline environments |
| Local compute | N/A (device stays on-premises) | Edge computing with Lambda or EKS Anywhere |

**Import job:**

```bash
# Create an import job
JOB_ID=$(aws snowball create-job \
  --job-type IMPORT \
  --resources S3Resources='[{BucketArn=arn:aws:s3:::my-import-bucket}]' \
  --address-id addr-xxxx \
  --snowball-type EDGE_STORAGE_OPTIMIZED \
  --description "Data migration to S3" \
  --shipping-option NEXT_DAY \
  --notification JobStateChangesOnly=true \
  --region us-east-1 \
  --query 'JobId' --output text)
```

**Export job:**

```bash
aws snowball create-job \
  --job-type EXPORT \
  --resources S3Resources='[{BucketArn=arn:aws:s3:::my-export-bucket}]' \
  --address-id addr-xxxx \
  --snowball-type EDGE_STORAGE_OPTIMIZED \
  --description "Export data from S3" \
  --shipping-option NEXT_DAY \
  --region us-east-1
```

## Step 2 — Device type selection

| Device | Usable storage | Compute | Weight | Use case |
|---|---|---|---|---|
| Edge Storage Optimized (210 TB) | 210 TB HDD | Optional Lambda | 49.7 lb | Large-scale data migration |
| Edge Storage Optimized (80 TB) | 80 TB HDD | Optional Lambda | 49.7 lb | Medium data migration |
| Edge Compute Optimized | 80 TB HDD + 7.68 NVMe | Lambda, EC2 (AMI) | 49.7 lb | Edge compute + data transfer |
| Snowcone | 8 TB HDD | Optional Lambda | 4.5 lb | Small transfers, space-constrained |
| Snowcone SSD | 14 TB NVMe | Optional Lambda | 4.5 lb | Small transfers, high IOPS |

**Device type is immutable after job creation.** To change types,
cancel the job and create a new one.

## Step 3 — S3 bucket configuration

For import jobs, the S3 bucket is the destination. For export jobs, it
is the source. The bucket must exist before job creation.

```bash
# Verify the destination/source bucket exists
aws s3api head-bucket --bucket my-import-bucket --region us-east-1

# Verify the bucket region
aws s3api get-bucket-location --bucket my-import-bucket
```

**Multiple buckets:** an import job can transfer data to multiple S3
buckets. An export job can export from only ONE bucket per job.

## Step 4 — Device pairing and unlock

After receiving the device, pair it with the AWS console and unlock it
using the snowballEdge CLI.

```bash
# Download the manifest from the AWS Snowball console (or CLI)
aws snowball get-job-manifest \
  --job-id $JOB_ID \
  --region us-east-1 \
  --query 'Manifest' --output text > manifest.bin

# Get the unlock code
aws snowball get-job-unlock-code \
  --job-id $JOB_ID \
  --region us-east-1 \
  --query 'UnlockCode' --output text

# Pair the device (on the device host)
snowballEdge configure-device \
  --device-ip-address 192.168.1.100 \
  --manifest-file manifest.bin \
  --unlock-code XXXX-XXXX-XXXX \
  --endpoint https://192.168.1.100:9091

# Unlock the device
snowballEdge unlock-device \
  --device-ip-address 192.168.1.100 \
  --manifest-file manifest.bin \
  --unlock-code XXXX-XXXX-XXXX \
  --endpoint https://192.168.1.100:9091
```

**Verify the device is unlocked:**

```bash
snowballEdge describe-device \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091
# Expected: device is UNLOCKED
```

## Step 5 — NFS interface for data transfer

Start the NFS interface on the unlocked device for file-based data
transfer.

```bash
# Start the NFS service on the device
snowballEdge start-service \
  --service-id nfs \
  --device-ip-address 192.168.1.100 \
  --manifest-file manifest.bin \
  --unlock-code XXXX-XXXX-XXXX \
  --endpoint https://192.168.1.100:9091

# Get the NFS IP address
snowballEdge describe-service \
  --service-id nfs \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091

# Mount NFS on the data transfer host
mount -t nfs -o nolock,hard 192.168.1.100:/nfs/path /mnt/snowball

# Copy data (parallel copy for performance)
find /data -type f | xargs -P 16 -I{} cp {} /mnt/snowball/
```

**Alternative: S3 adapter interface:**

```bash
# Use aws s3 cp with the device's S3 endpoint
aws s3 cp /data/ s3://snowball-bucket/ \
  --endpoint http://192.168.1.100:8080 \
  --recursive \
  --max-concurrent-requests 32
```

## Step 6 — Lambda functions for compute

Compute Optimized and Snowcone devices support Lambda functions for
edge processing. Deploy Lambda functions via the snowballEdge CLI.

```bash
# Create a Lambda function on the device
snowballEdge create-function \
  --function-arn arn:aws:lambda:us-east-1:123456789012:function:edge-processor \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091

# List deployed functions
snowballEdge list-functions \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091
```

Lambda functions on Snowball can process data locally (e.g., image
recognition, IoT data filtering) without cloud connectivity.

## Step 7 — Cluster mode (5-10 nodes)

Cluster mode connects 5-10 devices for compute resiliency. All nodes
must be the same device type and on the same network.

```bash
# Unlock all devices (repeat for each node)
for IP in 192.168.1.{100..104}; do
  snowballEdge unlock-device \
    --device-ip-address $IP \
    --manifest-file manifest-$IP.bin \
    --unlock-code XXXX-XXXX-XXXX \
    --endpoint https://$IP:9091
done

# Verify cluster status
snowballEdge describe-cluster \
  --device-ip-address 192.168.1.100 \
  --endpoint https://192.168.1.100:9091
```

**Cluster quorum:** a 5-node cluster tolerates 2 node failures.
A 10-node cluster tolerates up to 5 failures (but min 5 must remain).

## Step 8 — Shipping, tracking, and return

AWS manages shipping logistics. Track the device through the AWS
console or CLI.

```bash
# Check job status (includes shipping tracking)
aws snowball describe-job \
  --job-id $JOB_ID \
  --region us-east-1 \
  --query 'JobMetadata.{JobState:JobState,ShippingDetails:ShippingDetails}'
```

**For import jobs:** return the device using the AWS-provided shipping
label. AWS uploads data to S3 after receiving the device.

**For export jobs:** the device arrives pre-loaded with your S3 data.
After copying data off the device, return it to AWS.

## Step 9 — Data validation and reporting

After AWS processes the returned device (import), a data validation
report is available in the console.

```bash
# Check the job completion status and report
aws snowball describe-job \
  --job-id $JOB_ID \
  --region us-east-1 \
  --query 'JobMetadata.{JobState:JobState,JobLogInfo:JobLogInfo}'
```

The report includes:
- Number of objects successfully transferred.
- Number of objects that failed (with error details).
- Total data transferred.
- Transfer start and end times.

## Step 10 — EKS Anywhere and long-term rental

**EKS Anywhere on Snowball:**

EKS Anywhere can run on a Snowball Edge cluster (5+ nodes) for
persistent edge Kubernetes. This is for long-term edge computing
deployments, not temporary data migration.

**Long-term rental:**

Snowball Edge devices can be rented for 1-year or 3-year terms for
persistent edge deployments. This is cost-effective for continuous
edge computing (IoT processing, ML inference at remote sites).

```bash
# Create a long-term rental job (1-year)
aws snowball create-job \
  --job-type LOCAL_USE \
  --snowball-type EDGE_COMPUTE_OPTIMIZED \
  --address-id addr-xxxx \
  --description "Edge compute - long-term" \
  --shipping-option NEXT_DAY \
  --region us-east-1
```

**Recent features (2023-2026):**

- **Snowball Edge Compute Optimized with GPU (2023-2024):** AWS
  introduced Compute Optimized devices with optional NVIDIA GPUs for
  ML inference at the edge, supporting models that cannot run on CPU.

- **EKS Anywhere on Snowball maturity (2023-2024):** Enhanced EKS
  Anywhere support for Snowball Edge clusters, including automated
  cluster lifecycle management and simplified upgrade paths.

- **Snowcone long-term rental (2023-2024):** Snowcone devices now
  support 1-year and 3-year rental terms for persistent edge
  deployments in space-constrained environments.

- **Improved data transfer reporting (2023-2024):** Enhanced job
  completion reports with per-object status, error categorization,
  and downloadable CSV summaries for audit and compliance.

- **Snowball Edge 210 TB device (2024-2025):** AWS increased the
  Storage Optimized device capacity to 210 TB usable, reducing the
  number of devices needed for large-scale migrations.

- **Faster NFS throughput (2024-2025):** NFS interface throughput
  improvements, supporting up to 800 Mbps per connection on
  Storage Optimized devices with 100 GbE networking.

## NEVER do these things

1. **NEVER assume the device uploads data to S3 in real-time.** For
   import jobs, data is uploaded ONLY after the device is physically
   returned to AWS. The device is a physical shuttle, not a network
   gateway.

2. **NEVER try to change the job type after creation.** Job type
   (IMPORT, EXPORT, LOCAL_USE) is immutable. Cancel the job and create
   a new one if the type is wrong.

3. **NEVER use cluster mode for storage aggregation.** Cluster mode
   is for compute resiliency (5-10 nodes for HA), not for pooling
   storage. For large data transfers, use multiple single-device jobs.

4. **NEVER forget to start the NFS interface after unlock.** NFS does
   not auto-start. A common blocker is assuming the NFS share is
   available immediately after unlock without running `start-service`.

5. **NEVER reuse a manifest across jobs.** Each job has its own
   manifest and unlock code. Using a manifest from a different job
   fails the pairing step.

6. **NEVER ship the device back without stopping the NFS service
   first.** Stop the NFS service and gracefully power off the device
   before return shipping to avoid data corruption.

7. **NEVER export from multiple S3 buckets in a single export job.**
   Export jobs support only ONE source bucket per job. For multiple
   buckets, create separate export jobs.

8. **NEVER deploy EKS Anywhere on a single Snowball Edge device.**
   EKS Anywhere requires a minimum of 5 devices in cluster mode for
   quorum and resiliency. A single node cannot run EKS Anywhere.

9. **NEVER underestimate transfer time.** NFS transfer at 400-800 Mbps
   means 210 TB takes 3-6 days of continuous copying. Plan the transfer
   window accordingly and use parallel copy threads.

10. **NEVER forget to verify data after import.** After AWS processes
    the returned device, check the data validation report for failed
    objects. Re-transfer any failed objects with a new import job.

## Output format

```text
SNOWBALL_EDGE: <job-id> (<job-type>) — <device-type>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Job type: Import | Export | Local Use (compute)
  [✓|✗] Device type: Edge Storage Optimized (210 TB) | Edge Storage Optimized (80 TB) | Edge Compute Optimized | Snowcone | Snowcone SSD
  [✓|✗] S3 bucket: <bucket-name> (region: <region>) — <destination (import) | source (export)>
  [✓|✗] Shipping address: <address-id> — verified
  [✓|✗] Snowball type: EDGE_STORAGE_OPTIMIZED | EDGE_COMPUTE_OPTIMIZED | SNOWCONE | SNOWCONE_SSD
  [✓|✗] Cluster mode: <node-count> nodes (quorum: N) | single device
  [✓|✗] Device unlock: manifest applied, device UNLOCKED
  [✓|✗] NFS interface: started (IP: <device-ip>, mount: /nfs/path)
  [✓|✗] S3 adapter: available (endpoint: http://<device-ip>:8080)
  [✓|✗] Lambda functions: <count> deployed | not applicable
  [✓|✗] Data transfer plan: NFS parallel copy (<thread-count> threads) | aws s3 cp (max-concurrent-requests: <n>)
  [✓|✗] Return shipping: label available | planned
  [✓|✗] Data validation: report will be available in console after return | N/A
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws snowball describe-job --job-id <job-id> --region <region>
  aws snowball list-jobs --region <region>
  snowballEdge describe-device --endpoint https://<device-ip>:9091
```

### Worked example — import job with NFS transfer

```text
SNOWBALL_EDGE: JID12345678-1234-4321-1234-123456789012 (IMPORT) — EDGE_STORAGE_OPTIMIZED
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Job type: Import (on-premises → S3)
  [✓] Device type: Edge Storage Optimized (210 TB usable)
  [✓] S3 bucket: my-migration-bucket (region: us-east-1) — destination
  [✓] Shipping address: addr-aaaabbbb — verified
  [✓] Snowball type: EDGE_STORAGE_OPTIMIZED
  [✓] Cluster mode: single device
  [✓] Device unlock: manifest applied, device UNLOCKED
  [✓] NFS interface: started (IP: 192.168.1.100, mount: /nfs/data)
  [✓] Data transfer plan: NFS parallel copy (16 threads)
  [✓] Return shipping: AWS-provided label in console
  [✓] Data validation: report will be available after device return
  [✓] Tags: Environment=migration, Project=data-lift
VERIFICATION_COMMANDS:
  aws snowball describe-job --job-id JID12345678-1234-4321-1234-123456789012 --region us-east-1
  snowballEdge describe-device --endpoint https://192.168.1.100:9091
```

## Error handling

### Job creation fails — S3 bucket not found
- The S3 bucket must exist before creating the job. Verify with
  `aws s3api head-bucket`. Create the bucket if needed, then retry.

### Device pairing fails — manifest mismatch
- The manifest is job-specific. Download the correct manifest from
  the AWS Snowball console for THIS job. Do not reuse manifests from
  other jobs.

### NFS mount fails — service not started
- Start the NFS service via `snowballEdge start-service --service-id nfs`
  after unlock. NFS does not auto-start.

### Data transfer is slow
- Use parallel copy threads (`xargs -P 16`) for NFS, or increase
  `--max-concurrent-requests` for the S3 adapter. Verify the network
  link speed (100 GbE is optimal; 1 GbE is a bottleneck).

### Cluster formation fails — nodes not visible
- Verify all nodes are on the same network with mutual visibility.
  Check firewall rules and subnet configuration. All nodes must be the
  same device type.

## Domain

AWS CloudOps / AWS Snowball Edge Provisioning & Bulk Data Migration.

## AWS documentation

- **Snowball Edge Developer Guide** — https://docs.aws.amazon.com/snowball/latest/developer-guide/whatsnew.html
- **Create a job** — https://docs.aws.amazon.com/snowball/latest/developer-guide/create-job.html
- **Device unlock** — https://docs.aws.amazon.com/snowball/latest/developer-guide/unlock-device.html
- **NFS interface** — https://docs.aws.amazon.com/snowball/latest/developer-guide/using-nfs.html
- **Lambda on Snowball** — https://docs.aws.amazon.com/snowball/latest/developer-guide/lambda.html
- **Cluster mode** — https://docs.aws.amazon.com/snowball/latest/developer-guide/cluster.html
- **EKS Anywhere** — https://docs.aws.amazon.com/snowball/latest/developer-guide/eks-anywhere.html
- **Quotas** — https://docs.aws.amazon.com/snowball/latest/developer-guide/limits.html
