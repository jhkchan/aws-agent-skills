# Advanced Patterns — S3 Outposts Deployer

Deep-dive material moved from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset: three misconceptions that dominate S3 on Outposts misdesign

Three misconceptions dominate S3 on Outposts misdesign at provisioning
time:

- **"S3 on Outposts works like cloud S3."** It does NOT. S3 on Outposts
  has significant constraints: no public access (endpoint required),
  only STANDARD storage class (no IA, no Glacier), SSE-S3 encryption
  only (no SSE-KMS), lifecycle rules can only transition within the
  Outpost (no cloud tier transitions), and replication is one-way
  (Outpost to cloud, not cloud to Outpost). Treating it like cloud S3
  leads to failed API calls and broken workflows.

- **"You can access S3 on Outposts from the public internet."** You
  CANNOT. S3 on Outposts requires a VPC endpoint (S3 Outposts endpoint)
  to route traffic from the VPC to the Outpost. There is no public API
  endpoint. Without the endpoint, all S3 API calls to the outpost bucket
  fail with connection errors. This is the #1 cause of "can't access my
  outpost S3 bucket" issues.

- **"KMS encryption works on Outposts S3."** It does NOT. S3 on
  Outposts supports SSE-S3 (Amazon S3 managed keys) only. SSE-KMS is
  NOT supported on Outpost S3 buckets. If compliance requires KMS, data
  must be replicated to cloud S3 where SSE-KMS is available. This is
  a hard limitation of the Outpost S3 implementation.

## Configuration dependency graph: cross-dependency gotchas

**Cross-dependency gotchas:**
- The endpoint ties the Outpost to a specific VPC and subnet. All S3
  API calls must route through this endpoint. EC2 instances on the
  Outpost access the bucket via the endpoint.
- Access points create simplified names for bucket access. Outpost
  access points are different from cloud S3 access points — they
  require the endpoint to resolve.
- Object lock must be enabled at bucket CREATION time. It cannot be
  enabled later. If you need WORM and did not enable it at creation,
  you must create a new bucket.
- Replication is one-way only. The Outpost bucket replicates TO a cloud
  bucket. The cloud bucket cannot replicate back to the Outpost.

## Expert heuristic: endpoint is the mandatory networking bridge

A baseline model creates the bucket and assumes it is accessible. The
correct heuristic recognizes that S3 on Outposts has NO public endpoint
— ALL access goes through a VPC endpoint.

```text
Cloud S3:
  Client → public S3 API endpoint → AWS cloud → bucket

S3 on Outposts:
  Client → VPC endpoint (on Outpost) → Outpost S3 → bucket
              ↑ REQUIRED — no public API for Outpost S3

Without endpoint:
  aws s3 ls s3://my-outpost-bucket → connection timeout / access denied
```

**Key implication:** the endpoint must exist in a VPC that has
connectivity to the Outpost. Typically this is a VPC with subnets on
the Outpost. EC2 instances on the Outpost access the bucket via the
endpoint.

## Expert heuristic: one-way replication and capacity

A baseline model may assume replication is bidirectional. The correct
heuristic recognizes that S3 on Outposts replication is one-way
(Outpost to cloud only), driven by the finite physical storage of the
Outpost rack.

```text
Replication direction:
  Outpost bucket → Cloud bucket  ✓ (supported, one-way)
  Cloud bucket → Outpost bucket  ✗ (not supported)

Capacity management:
  Outpost storage is FINITE (physical disks on the rack)
  → Monitor used capacity via CloudWatch
  → Use replication to cloud as a drain mechanism
  → Use lifecycle rules to manage object retention on Outpost
  → When capacity is full, writes FAIL (no elastic expansion)
```

## Expert heuristic: object lock at creation only

A baseline model may think object lock can be enabled after bucket
creation. The correct heuristic recognizes that object lock MUST be
enabled at bucket creation time and CANNOT be added later.

```text
Bucket creation with object lock:
  aws s3control create-bucket --outpost-id op-xxx --object-lock-enabled

If you forgot:
  Cannot enable after creation.
  Must create a new bucket with --object-lock-enabled.
  Must migrate objects to the new bucket.
```

