# Error Handling — s3-secure-bucket-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

### Step 1 — Block Public Access

**If it fails**: `AccessDenied` means the caller lacks
`s3:PutBucketPublicAccessBlock` (bucket-level) or
`s3:PutAccountPublicAccessBlock` (account-level) — these are separate
IAM permissions and both must be in the caller's policy. `NoSuchBucket`
on the bucket-level call means the bucket does not exist yet; create
it first (and apply bucket-level BPA in the same CloudFormation stack
or Terraform run as the create, so the public-exposure window is zero).

---

### Step 2 — Default encryption

**If it fails**: `KMSNotFoundException` or `AccessDenied` on the
SSE-KMS call almost always means ONE of: (a) the KMS key ARN region
or account ID is wrong, (b) the key is in `PendingDeletion` state,
(c) the key policy does not grant the S3 service principal
`kms:Encrypt` + `kms:GenerateDataKey` — verify with
`aws kms describe-key --key-id <ARN>` and inspect the policy with
`aws kms get-key-policy`. `MalformedJSON` usually means shell escaping
ate the inner double-quotes — wrap the JSON in single quotes.

---

### Step 3 — Object Ownership

**If it fails**: `AccessDenied` means the caller lacks
`s3:PutBucketOwnershipControls` (separate from `s3:PutBucketPolicy`).
`OwnershipControlsNotFoundError` is benign on a brand-new bucket —
re-issue the call once.

---

### Step 4 — Versioning

**If it fails**: `AccessDenied` on the MFA Delete call almost always
means the caller is an IAM principal rather than root — re-run with
root account credentials (and rotate them after). `InvalidArgument` on
the `--mfa` flag means the device ARN or code is wrong, or the device
is not yet attached to the root account.

---

### Step 5 — Bucket policy

**If it fails**: `AccessDenied` usually means BPA's
`BlockPublicPolicy=true` is blocking a policy containing `Principal: "*"`
with `Allow` (our deny policies should pass). `MalformedPolicy` means
JSON syntax error — validate with `python -m json.tool policy.json` or
`jq . policy.json`. `NoSuchBucket` means the bucket doesn't exist yet.

---

### Step 6 — Access logging

**If it fails**: `put-bucket-logging` returns 200 even when the log
target is misconfigured — the only signal is that no logs appear after
1+ hours. Diagnostic order: (1) `aws s3api get-bucket-logging --bucket
<LOG-BUCKET>` to confirm S3 log delivery is the configured target;
(2) verify log target exists in the SAME region as the source bucket
(cross-region log delivery is unsupported for S3 server access logs);
(3) check the log target's bucket policy for the
`logging.s3.amazonaws.com` grant. CloudTrail `TrailNotFoundException`
means the trail name is wrong or the trail is in a different region.

---

### Step 7 — Lifecycle rules

**If it fails**: `MalformedXML` almost always means the `Filter` element
is missing — every modern rule requires `"Filter": {"Prefix": ""}` even
when matching all objects. If rules apply but objects do not transition,
verify (a) versioning is `Enabled`, (b) the object has been in its
current storage class for at least the minimum duration (30 / 60 / 90 /
180 days), and (c) for `NoncurrentVersion*` rules, the object has at
least one non-current version (a bucket with no overwrites has none).

---

### Step 8 — Replication

**If it fails**: `InvalidRequest` typically means versioning is not
enabled on the SOURCE or the DESTINATION bucket (both are required).
`AccessDenied` on the role assume means the trust policy doesn't list
`s3.amazonaws.com` as principal, or the role doesn't exist in this
account. If the call succeeds but replicas do not appear, check the
replication role's permissions: it needs `s3:ReplicateObject` AND
`s3:GetObjectVersionForReplication` on source + `kms:Decrypt` on the
source KMS key + `kms:Encrypt` / `kms:GenerateDataKey` on the
destination KMS key. Use S3 replication metrics (`S3:ReplicationLatency`,
`S3:BytesPendingReplication`) to detect silent stalls.
