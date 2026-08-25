# Advanced Patterns — Snowball Edge Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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

## Recent AWS features (2023-2026)

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
