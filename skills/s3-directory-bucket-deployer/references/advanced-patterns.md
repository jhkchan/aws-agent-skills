# Advanced Patterns — s3-directory-bucket-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Expert heuristic: the zone-mismatch trap


The most dangerous directory bucket misconfiguration: compute in a
different AZ than the bucket.

```text
Operator thinks:              What actually happens:
"Same region" is enough  →   The directory bucket is in exactly one AZ;
                               EC2 in a different AZ of the same region
                               pays $0.01/GB cross-AZ transfer each way
                               and sees ~10x higher latency than zone-
                               affinity placement. No error is surfaced;
                               the workload just costs more and runs
                               slower with no signal.
```

The tell-tale signal: S3 request latency is 10-50ms instead of
single-digit milliseconds, and Cost Explorer shows Data Transfer -
Regional line items between EC2 and S3 in the same region. Remedy:
pin compute to the directory bucket's AZ using subnet AZ filtering
or an EC2 Capacity Reservation in that AZ; verify with a latency
probe (`time aws s3 ls s3://<bucket> --region <region>`).

---

## Expert heuristic: the name format parser


Directory bucket names have a rigid structure that encodes the AZ:

```text
  my-app-data--use1-az1--x-s3
  ^^^^^^^^^^^   ^^^^^^^^ ^^^^^
  base name     AZ ID    mandatory suffix
```

Rules a baseline model misses:

1. **Double-dash (`--`) is the delimiter, not single dash.** A base
   name containing `--` collides with the parser and is rejected.

2. **The AZ ID is NOT the AZ name.** `use1-az1` maps to `us-east-1a`
   but the mapping is account-specific (AZ `us-east-1a` for account A
   may map to `use1-az4` for account B). Always resolve with
   `ec2 describe-availability-zones --zone-names us-east-1a`.

3. **The `--x-s3` suffix is mandatory.** Without it, the API rejects
   the name. Operators who drop the suffix and switch to `create-bucket`
   silently create a general-purpose bucket.

4. **The base name must be DNS-compatible and globally unique within
   the AZ.** Directory bucket names are not globally unique across all
   AWS like standard buckets, but they must be unique within the AZ.

---

## Expert heuristic: table bucket API divergence


S3 Tables table buckets are a directory bucket type for Apache Iceberg
tables. The API surface is `aws s3tables`, not `aws s3api`:

```bash
# WRONG — plain directory bucket, no table semantics
aws s3api create-directory-bucket --bucket my-iceberg--use1-az1--x-s3 ...

# CORRECT — table bucket via the S3 Tables API
aws s3tables create-table-bucket \
  --name my-iceberg-tables \
  --region use1-az1
```

The `--region` parameter for `create-table-bucket` takes the AZ ID
(e.g., `use1-az1`), not a standard region string. Table buckets
support table-level operations (`create-table`, `get-table`,
`put-table-data`), not object-level operations. Operators who try to
`PutObject` into a table bucket get an error because the API surface is
fundamentally different.

---

## Recent AWS features


- **S3 Tables (table buckets)**: S3 Tables provides fully managed Apache
  Iceberg table storage in directory buckets. Created via `aws s3tables
  create-table-bucket` with the AZ ID as the region parameter. Table
  buckets support table-level operations and integrate with Athena,
  Glue, Spark, and Trino for analytics workloads. They do NOT support
  object-level operations (`PutObject`/`GetObject`).

- **AZ ID targeting for directory buckets**: directory buckets encode
  the AZ ID directly in the bucket name (`base--az-id--x-s3`), allowing
  precise single-AZ placement. The AZ ID is account-specific and must
  be resolved from the AZ name via `ec2 describe-availability-zones`.

- **Zone-optimized compute placement**: EC2, ECS, and EKS support
  Availability Zone ID targeting for co-locating compute with directory
  buckets. Use subnet AZ filtering or capacity reservations to pin
  compute to the directory bucket's AZ. This is the key configuration
  that delivers the single-digit-millisecond latency and highest
  requests-per-second throughput.

- **S3 Express One Zone pricing**: Express One Zone has the lowest
  latency and highest requests-per-second of any S3 tier. Pricing
  includes charges for PUT/POST/LIST requests, GET/SELECT requests,
  data retrieval, and storage. Data transfer between a directory bucket
  and compute in the same AZ is free; cross-AZ transfer incurs standard
  regional data-transfer fees.

- **Zonal endpoint auto-routing**: the AWS SDK and CLI auto-resolve the
  Zonal endpoint from the directory bucket name format. Applications
  should NOT override the endpoint to a regional endpoint — doing so
  adds routing overhead and negates the latency benefit.

- **SSE-KMS support**: directory buckets support both SSE-S3 (default)
  and SSE-KMS with a customer-managed key. The KMS key must be in the
  same region as the directory bucket.
