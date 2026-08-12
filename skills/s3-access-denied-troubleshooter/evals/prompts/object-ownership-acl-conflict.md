# Eval prompt: object-ownership-acl-conflict

Diagnose the S3 Access Denied error for the following scenario. Walk
the authorisation evaluation hierarchy and emit the standard diagnostic
block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: role `arn:aws:iam::111111111111:role/data-reader` gets
"Access Denied" on `s3:GetObject` for SOME objects in
`shared-upload-bucket`. The bucket policy allows the role. Some
objects are accessible; others are not. The inaccessible objects
were uploaded by a cross-account partner (account 222222222222).

```text
Bucket: shared-upload-bucket (owner: 111111111111)
Caller: arn:aws:iam::111111111111:role/data-reader
Action: s3:GetObject
Error: "Access Denied" (HTTP 403) — on SOME objects only

IAM policy (data-reader):
  - Allow s3:GetObject on arn:aws:s3:::shared-upload-bucket/*

Bucket policy:
  - Allow s3:GetObject for principal
    arn:aws:iam::111111111111:role/data-reader

Object ownership: ObjectWriter (NOT BucketOwnerEnforced)
Encryption: SSE-S3

Object ACL (accessible object):
  Owner: 111111111111 (bucket owner)
  Grants: full control to bucket owner

Object ACL (denied object):
  Owner: 222222222222 (uploader — different account)
  Grants: full control to 222222222222 only
  (no grant to the bucket owner 111111111111)

SCPs: none deny s3
KMS: not in use
```

Object ownership determines who can grant access. When the bucket owner
is not the object uploader, the bucket policy cannot override the
object's ACL. Verify the ownership mismatch and recommend the fix.
