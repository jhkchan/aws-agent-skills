# Advanced Patterns — S3 Access Troubleshooter

Load-on-demand deep dives moved verbatim from SKILL.md: the Mindset
facts, the expert edge cases, and recent AWS features.

## Mindset — three facts (full)

Three facts make S3 troubleshooting different from generic "check your
policy":

- **ARN shape determines which actions can match.** The single most
  common S3 misdiagnosis is "the policy has `s3:GetObject` on the bucket
  ARN." For S3, bucket-level actions (`s3:ListBucket`,
  `s3:DeleteBucket`, `s3:GetBucketLocation`) require
  `arn:aws:s3:::bucket-name` (no `/*`). Object-level actions
  (`s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`) require
  `arn:aws:s3:::bucket-name/*` (with `/*`). Confusing the two produces
  AccessDenied on a policy that "looks right."

- **Account-level BPA overrides everything below it.** The BPA hierarchy
  in AWS's evaluation is `account-level BPA > bucket-level BPA > ACL >
  bucket policy > IAM identity policy`. Account-level BPA blocks public
  access even if the bucket policy explicitly allows `Principal: "*"` —
  and SILENTLY. There is no error; the request is denied as if no policy
  allowed it. Operators chasing a bucket-policy bug while account-level
  BPA is the cause waste hours.

- **KMS is a separate decision gate, not part of the bucket policy.** A
  bucket encrypted with a customer-managed KMS key has TWO independent
  access decisions: the S3 layer (bucket policy + identity policy) AND
  the KMS layer (key policy + identity policy's `kms:Decrypt` grant).
  Each gate can independently deny. The same principal may have S3
  access but no KMS access — the symptom is AccessDenied on GetObject,
  indistinguishable from a pure S3 deny without inspecting CloudTrail.

## Expert edge cases

### The `aws:SourceAccount` chain on S3 → KMS

When S3 reads an object encrypted with a KMS key on behalf of a caller,
the KMS `Decrypt` call is made BY S3 — not by the caller directly. A KMS
key policy that requires
`aws:SourceAccount: "<caller-acct>"` evaluates the S3 service call's
source account — which is the BUCKET's account, not the caller's.

Operators writing this condition expecting it to mean "the caller's
account" produce silent denies. Fix: scope on `aws:SourceArn` of the
bucket, OR list the bucket's account in `aws:SourceAccount`.

### VPC endpoint policy shadow

A VPC endpoint has its own policy independent of IAM. If a VPC endpoint
policy denies an action, the request fails even though every IAM policy
allows it. The CloudTrail event shows AccessDenied with no hint about
the VPC endpoint policy. The diagnostic is to bypass the endpoint (route
over the internet or a different endpoint) and see if the call succeeds.

VPC endpoint policies are the most overlooked layer because they live in
the VPC console, not IAM.

### CloudFront OAC replaces OAI

The legacy CloudFront Origin Access Identity (OAI) used a special IAM
principal (`arn:aws:iam::cloudfront:user/CloudFront Origin Access
Identity <id>`). The modern Origin Access Control (OAC) uses a service
principal (`service:cloudfront.amazonaws.com`) with the distribution ARN
in `aws:SourceArn` condition.

A bucket policy still using the OAI principal blocks OAC-authenticated
CloudFront requests. The error is 403 from CloudFront (origin denied).
Migrate the bucket policy to the OAC format when migrating from OAI.

### S3 Access Point bypasses bucket policy

Each Access Point has its own policy. Requests addressed through the AP
ARN are evaluated against the UNION of the bucket policy and the AP
policy. A restrictive bucket policy does NOT prevent access through a
permissive Access Point. Always enumerate APs and audit their policies
independently.

### Object Lock retention is irreversible for COMPLIANCE mode

An object under `COMPLIANCE` retention cannot be overwritten or deleted
by ANY principal — including root — until the retain-until date. The
error is 403 AccessDenied. `GOVERNANCE` mode can be bypassed by a
principal with `s3:BypassGovernanceRetention` permission (and root has
this by default). Verify the mode (`COMPLIANCE` vs `GOVERNANCE`) before
recommending a fix.

### Cross-account write to a `BucketOwnerEnforced` bucket

Object Ownership `BucketOwnerEnforced` (default for new buckets since
April 2022) disables ACLs entirely. Cross-account writers cannot use
ACL-based ownership transfer. They MUST include
`x-amz-acl: bucket-owner-full-control` in the PutObject request AND the
bucket policy must Allow the action for the cross-account principal.

This is the most common cause of "cross-account uploads were working
before but now fail" after a bucket ownership-controls migration.

### Presigned URL with a Session Policy

When a presigned URL is signed by an assumed-role session, the session
policy that was active at signing is enforced at request time. If the
session policy narrows the effective permissions (e.g., allows
`s3:GetObject` only on `personal-${aws:username}/*`), the presigned URL
fails for any key outside that pattern.

The session policy is NOT visible in the presigned URL — it must be
inferred from the `assumeRole` request parameters in CloudTrail.

### S3 directory buckets have different access semantics

S3 Directory Buckets (`<prefix>--x-s3` — used for S3 Express One Zone)
use Zonal Endpoints with different authentication. Standard S3 presigned
URLs do NOT work against directory buckets — they require
directory-bucket-specific signing. The error is 403 with no hint about
the bucket type. Verify the bucket type via
`aws s3api list-buckets --query 'Buckets[?Name==`<name>`].BucketType'`.

### Multi-Region Access Point (MRAP) policy propagation

A MRAP policy applies to requests through the MRAP ARN. Each underlying
regional bucket also has its own policy. The effective permission is the
union of MRAP policy + regional bucket policy. A permissive MRAP policy
exposes ALL regional buckets. Audit MRAP policy via
`aws s3control get-multi-region-access-point-policy`.

## Recent AWS features (2024-2026)

- **S3 directory buckets (S3 Express One Zone) (2024-2025):** Single-AZ,
  single-digit-millisecond latency. Different authentication model —
  standard presigned URLs do NOT work. Zonal endpoint API only.
- **S3 Access Grants (2024):** Identity-based access management for S3
  data. Troubleshoot access via Access Grants instance + IAM role for
  Access Grants. Replaces some bucket-policy use cases.
- **S3 Tables (2024-2025):** Managed tabular storage (Apache Iceberg) in
  S3. Table bucket policies follow the same BPA and encryption model as
  standard buckets.
- **S3 Object Versioning default (2024-2025):** AWS is moving toward
  enabling Versioning by default on new buckets. Troubleshoot
  DeleteObject on versioned buckets separately (DeleteObject vs
  DeleteObjectVersion).
- **CloudFront OAC mandatory for new distributions (2024-2025):** New
  CloudFront distributions should use OAC. OAI is legacy. Bucket policies
  must use the OAC principal format.
- **BPA account-level default (2024-2025):** AWS is enabling account-level
  BPA by default on new accounts. Troubleshoot "public access was working
  before" by checking if account-level BPA was enabled by AWS during a
  recent account refresh.
- **Cross-Region Access Logging for DataSync / Multi-Region Access
  Points (2024-2025):** MRAP policies can now propagate access logs to
  multiple regions. Troubleshoot MRAP access by checking the policy at
  the MRAP ARN, not just the regional bucket.
