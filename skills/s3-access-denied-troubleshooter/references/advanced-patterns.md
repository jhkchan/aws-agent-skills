# Advanced Patterns — S3 Access Denied Troubleshooter

Mindset, philosophy, Step 0 non-obvious behaviours, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Mindset

An S3 Access Denied error is almost never about the application code.
The application is making a valid S3 API call; the authorisation layer
is rejecting it. The root cause is somewhere in the policy evaluation
chain: SCP, IAM identity policy, bucket policy, KMS key policy,
permission boundary, session policy, VPC endpoint policy, or one of
the non-policy gates (object ownership, Block Public Access, Object
Lock, presigned URL validity, Object Lambda routing). Senior storage
engineers start with the policy evaluation hierarchy and work outward
to the non-policy gates; they do not start by re-reading the
application SDK call.

## Philosophy

Four behaviours separate a senior S3 engineer from a generalist:

- **The policy evaluation hierarchy is strict and non-negotiable.** The
  evaluation order is: (1) SCPs at every org/OU level (a deny at any
  level blocks the request before it reaches IAM), (2) IAM identity
  policy (the caller's attached and inline policies), (3) bucket policy
  (the resource-based policy on the bucket), (4) KMS key policy (if
  the object is SSE-KMS encrypted). An explicit Deny at any level
  overrides all Allow statements at all levels. Operators who "added
  the IAM permission" but still see AccessDenied often miss an explicit
  Deny in an SCP, bucket policy, or permission boundary.
- **Explicit deny and implicit deny produce the same error but require
  different fixes.** An explicit deny means a `Deny` statement exists
  somewhere in the hierarchy and must be removed or scoped narrower.
  An implicit deny means no `Allow` statement exists at all — the
  permission was never granted. CloudTrail's `errorMessage` field
  distinguishes the two: "explicit deny" vs a bare "Access Denied."
  Operators who treat both the same waste time searching for a Deny
  statement that does not exist.
- **KMS is a separate gate from S3.** When an object is encrypted with
  a customer-managed KMS key, the caller must have `kms:Decrypt` (IAM)
  AND the key policy must allow the caller's account to use the key.
  The S3 service makes the `kms:Decrypt` call on behalf of the user;
  the IAM permission is checked against the caller's identity. A
  missing KMS grant produces the same `Access Denied` error as a
  missing S3 permission — the error message does not name KMS.
- **Object ownership is invisible until it bites.** Before the
  `BucketOwnerEnforced` setting (default for new buckets since April
  2023), the uploader owned the object and ACLs controlled access. A
  bucket owner's policy could not override ACLs on objects they did
  not own. Operators migrating from cross-account upload patterns
  discover that their bucket policy "works" for some objects but not
  others — the difference is who uploaded each object.

## Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior S3 engineer knows from
incident experience:

- **S3 AccessDenied does not distinguish between S3-layer and KMS-layer
  denial.** When an object is SSE-KMS encrypted, the S3 service calls
  `kms:Decrypt` on behalf of the caller. If the caller lacks
  `kms:Decrypt`, S3 returns `Access Denied` — the same error string as
  a missing `s3:GetObject` permission. Operators who "fixed the S3
  policy" but still see AccessDenied on SSE-KMS objects are chasing
  the wrong layer.

- **An explicit Deny anywhere in the hierarchy overrides ALL Allow
  statements everywhere.** An SCP `Deny` at the org root blocks the
  request before IAM or bucket policies are evaluated. A bucket policy
  `Deny` blocks even if the IAM identity policy allows. A permission
  boundary `Deny` blocks even if the IAM policy allows. Always search
  for `Deny` statements at every level before concluding an implicit
  deny.

- **Cross-account S3 access requires mutual consent: the bucket policy
  must allow the caller's account, AND the caller's IAM policy must
  allow the S3 action.** Same-account access works with either side
  alone. Operators who "added the IAM permission" for a cross-account
  caller forget the bucket policy side; operators who "added the bucket
  policy" forget the IAM side.

- **Object Lock retention and legal holds produce AccessDenied on
  overwrite or delete, not on read.** An object in `COMPLIANCE` mode
  with an active retention period cannot be overwritten or deleted by
  ANY principal, including the root account. An object with a legal
  hold cannot be overwritten or deleted until the hold is removed. The
  error is `AccessDenied`, not "object locked."

- **Block Public Access at the bucket level blocks public reads even
  if the bucket policy explicitly allows `s3:GetObject` to `*`.** The
  Block Public Access settings are evaluated before the bucket policy.
  If `RestrictPublicBuckets` is enabled and the bucket policy has a
  public principal (`*`), the public access is blocked silently. The
  bucket owner's own access is unaffected.

- **S3 Object Lambda access points use a different ARN namespace.** An
  ARN like `arn:aws:s3-object-lambda:us-east-1:111111111111:accesspoint/`
  `my-olap` requires the caller to use the Object Lambda ARN, not the
  standard S3 ARN. Operators who paste the standard S3 bucket ARN get
  AccessDenied because the policy on the Object Lambda access point
  was never evaluated.

- **A VPC endpoint policy for S3 can restrict actions independently of
  IAM and bucket policy.** When traffic flows through an S3 Gateway
  endpoint, the endpoint policy is evaluated as an additional gate. An
  endpoint policy that allows only `s3:GetObject` blocks `s3:PutObject`
  even if IAM and bucket policy both allow it. The error is the same
  `Access Denied`.

- **Presigned URL expiry is checked at the S3 service edge.** A URL
  with `X-Amz-Expires=300` (5 minutes) that is used at minute 6 returns
  `AccessDenied` with the message "Request has expired." The
  `SignatureDoesNotMatch` error, by contrast, indicates the signature
  region or credentials used to sign differ from the region or
  credentials used at request time.

- **The `aws:SourceIp` condition in a bucket policy can block traffic
  from a NAT Gateway or VPC endpoint.** A policy that allows a
  corporate CIDR but not the VPC's NAT Gateway IP blocks VPC-attached
  workloads. When a VPC Gateway endpoint is used, the `aws:SourceIp`
  condition is NOT populated — `aws:SourceVpce` must be used instead.

- **STS assumed-role sessions carry the permission boundary and session
  policy as additional filters.** The effective permission for an
  assumed role is: IAM policy AND permission boundary AND session
  policy. Operators who assume a role with `--policy-arn` (a session
  policy) narrow the role's permissions for that session only; the
  role's own permissions are unchanged for other sessions.

## Recent AWS features (2024-2026)

- **S3 Object Ownership BucketOwnerEnforced default (2023-2024):** All
  new buckets default to `BucketOwnerEnforced`, disabling ACLs. This
  eliminates the object-ownership class of AccessDenied for new
  buckets. Existing buckets may still use `ObjectWriter` or
  `BucketOwnerPreferred`.
- **S3 Access Points cross-account (2024):** Access points support
  cross-account access via access point policies and IAM policies. The
  evaluation is: IAM policy AND access point policy must both allow.
- **S3 Batch Operations copy-in-place for ownership (2024-2025):**
  Batch Operations can copy objects in-place to change ownership when
  migrating to `BucketOwnerEnforced`. The copy operation reads the
  object with the uploader's permissions and writes it as the bucket
  owner.
- **S3 Object Lambda access point ARN (2024):** Object Lambda access
  points use the `s3-object-lambda` ARN namespace. Standard S3 SDK
  calls to an Object Lambda ARN fail; the caller must use the Object
  Lambda endpoint.
- **KMS key policy `kms:Decrypt` for S3 (2024-2026):** The KMS key
  policy must explicitly grant `kms:Decrypt` for the S3 service
  principal (`s3.<region>.amazonaws.com`) with the bucket ARN in the
  encryption context. Without this, SSE-KMS objects cannot be read.
