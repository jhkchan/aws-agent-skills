# Advanced Patterns — S3 Access Points Deployer

Load-on-demand deep dives moved verbatim from SKILL.md: the reasoning
framework, the expert heuristics, the Step 8 optional-feature
sub-procedures, and recent AWS features.

## Reasoning framework (why the provisioning order matters)

S3 Access Points look like "a named entry point to a bucket" but the
underlying model has four traps:

1. **An access point is a separate ARN with its own policy, but the
   BUCKET policy still applies cumulatively.** Effective permission on
   a request through the AP = (AP policy) ∩ (bucket policy) ∩ (IAM).
   A permissive bucket policy cannot be tightened by tightening the AP
   policy. A restrictive bucket policy can silently block AP traffic.

2. **The bucket's global hostname stays reachable after AP creation.**
   Creating a VPC-origin AP does NOT disable the
   `s3.<region>.amazonaws.com` path. A principal with `s3:GetObject`
   in the bucket policy still reaches data through the global hostname.
   The only way to make a bucket truly VPC-only is a bucket policy
   `Deny` with `Null: { s3:DataAccessPointArn: true }` — deny if the
   request did NOT come through an access point.

3. **The AP policy is NOT a subset of the bucket policy.** It is a
   parallel document. Operators who copy a bucket policy into the AP
   policy and leave the bucket ARN in `Resource` produce dead text —
   the AP ARN is the resource on AP-routed requests.

4. **MRAP and Object Lambda have their own silent-failure modes.** MRAP
   does not backfill. Object Lambda invokes synchronously; throttles
   surface to the client as S3 errors, not Lambda errors.

## Expert heuristic: the VPC-only invariant myth

The most dangerous misconception: "VPC network origin = bucket is
VPC-only." It is not.

```text
Operator thinks:       What actually happens:
VPC-origin AP →        VPC-origin AP →
  bucket VPC-only        bucket reachable from VPC via AP hostname
                         bucket ALSO reachable from anywhere via
                         s3.<region>.amazonaws.com
```

The VPC-origin setting controls the **network path to the AP hostname
only**. The global bucket hostname is unaffected. To make a bucket
truly VPC-only you need: (1) a VPC-origin AP (Step 2 + Step 4), (2) a
bucket policy `Deny` keyed on `Null: { s3:DataAccessPointArn: true }`
(Step 6), and optionally (3) a VPC endpoint policy restricting to the
AP ARN (Step 3). The wrong condition key is the most common
implementation bug: `aws:SourceVpce` / `aws:SourceVpc` are for VPC-
endpoint enforcement and are NOT set on AP-routed requests. The
correct key is `s3:DataAccessPointArn`.

## Expert heuristic: MRAP cost amplification and non-backfill

A Multi-Region Access Point looks like "one hostname, write/read
nearest region." Two operational truths are routinely missed:

1. **MRAP does not backfill.** Objects written before the MRAP was
   created are NOT visible through the MRAP hostname. Operators who
   expect "MRAP = one global namespace over all my data" get a partial
   namespace with no error signal. Remedy: Batch Operations copy.

2. **MRAP cross-region pricing is real.** A GET via the MRAP hostname
   billed at the serving region's rate; cross-region routing adds data
   transfer fees. At 100 TB/month of cross-region egress this is
   multiple thousands of dollars per month with no default alarm.
   Remedy: pin clients to regions, alarm on `BytesRequested` /
   `4xxErrors` per region, prefer failover-only topologies unless
   active-active is a hard product requirement.

## Expert heuristic: Object Lambda concurrency

Object Lambda invokes the transform function synchronously on every
GET. The function's concurrency budget IS the access point's
throughput ceiling — there is no S3-side queue. At throttle, clients
see S3-shaped errors (`AccessDenied`, `SlowDown`), NOT Lambda
`ThrottledException`. Operators blame S3. Remedy: set reserved
concurrency equal to expected peak GET rate, alarm on Lambda
`Throttles` and `Errors`, and log the original GET ARN for correlation.

## Step 8 — Optional: Object Lambda / MRAP / cross-account / alias (sub-procedures 8a-8e)

#### 8a. Object Lambda access point

Provision a supporting standard AP first (Steps 4-6), then create the
Object Lambda AP on top of it:

```bash
aws s3control create-access-point-for-object-lambda \
  --account-id <ACCOUNT_ID> \
  --name <OLAP_NAME> \
  --configuration \
    SupportingAccessPoint=arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>,\
    TransformationConfigurations='[{Action=GetObject,ContentTransformation=AWSLambda:{FunctionArn=arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC>}}]'
```

Set reserved concurrency on the transform function before traffic
starts; see the Object Lambda heuristic above.

#### 8b. Multi-Region Access Point (MRAP)

```bash
aws s3control create-multi-region-access-point \
  --account-id <ACCOUNT_ID> \
  --details Name=<MRAP_NAME>,Regions='[{Bucket=arn:aws:s3:::<BUCKET_A>},{Bucket=arn:aws:s3:::<BUCKET_B>}]'
```

Verify with `get-multi-region-access-point` (async — poll until READY).
Remember: pre-existing objects are NOT backfilled; copy them via Batch
Operations if they need to be reachable through the MRAP.

#### 8c. Cross-account access point

The bucket owner grants the foreign account `s3:CreateAccessPoint` in
the bucket policy:

```json
{
  "Sid": "DelegateAPCreation",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<FOREIGN_ACCOUNT>:root" },
  "Action": "s3:CreateAccessPoint",
  "Resource": "arn:aws:s3:::<BUCKET>"
}
```

The foreign account then runs `create-access-point` as in Step 4. The
foreign-owned AP uses the foreign account in the ARN — verify with
`get-access-point` and ensure the bucket owner's per-AP BPA posture
is not weakened.

#### 8d. Alias

Each access point gets an auto-generated alias (`<AP_NAME>-<random>.s3-accesspoint.<region>.amazonaws.com`)
that is DNS-compatible and can be used in CNAME records. There is no
explicit create step; verify with `get-access-point --query Alias`.
For a custom alias, register a CNAME in your DNS provider pointing to
the auto-generated alias hostname.

#### 8e. S3 on Outposts access points

Outposts APs use the `s3outposts` API and a different ARN namespace:

```bash
aws s3outposts create-access-point \
  --container-arn arn:aws:s3-outposts:<REGION>:<ACCOUNT>:outpost/<OUTPOST_ID>/bucket/<BUCKET> \
  --name <AP_NAME>
```

Do NOT use the regional `s3control create-access-point` for Outposts —
it returns success but does not provision the Outposts AP.

## Recent AWS features

- **S3 Access Points for S3 on Outposts**: separate `s3outposts` API
  and ARN namespace (`arn:aws:s3-outposts`). Regional `s3control`
  calls return success but do NOT provision the Outposts AP — verify
  with `s3outposts list-access-points`.
- **Multi-Region Access Points with failover controls**: active-passive
  failover via top-level `PublicDnsName` and route-control; objects
  written before MRAP creation still NOT backfilled.
- **Per-access-point Block Public Access**: separate `PutAccessPointPublicAccessBlock`
  API; distinct from bucket-level and account-level BPA.
- **Object Lambda runtime deprecation signals**: AWS guidance is to
  prefer S3 Batch Operations for transformation at write time when
  feasible; Object Lambda remains supported for transform-on-read.
- **Access Point alias auto-generation**: every AP gets a DNS-
  compatible alias; no manual registration needed for standard use.
- **Cross-account Access Point delegation**: bucket owner grants
  `s3:CreateAccessPoint` in the bucket policy; the foreign-owned AP
  is subject to the foreign account's policies, NOT the bucket
  owner's per-AP BPA — the bucket owner MUST add a bucket-policy
  condition on the AP ARN for containment.
