---
name: s3-access-denied-troubleshooter
description: 'Diagnoses Amazon S3 Access Denied errors through a thirteen-category diagnostic tree: explicit deny in bucket policy overriding an IAM allow, object ownership mismatch (bucket owner vs uploader), bucket owner enforcement (RequestAccount condition), KMS key policy missing kms:DecryptObject grant, VPC endpoint policy restricting S3 actions, presigned URL expiry or signature mismatch, ACL vs bucket policy conflict, Block Public Access settings, Object Lock retention preventing overwrite or delete, cross-account access requiring both bucket policy and IAM permission, STS assumed-role permission boundary narrowing effective permissions, Service Control Policy denying S3 at the org level, and S3 Object Lambda access point routing. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and bucket configuration. Live-account diagnosis uses aws s3api get-bucket-policy, aws s3api get-object-acl, aws s3api get-public-access-block, aws s3api get-object-lock-configuration, aws kms describe-key / get-key-policy, aws ec2 describe-vpc-endpoints, aws iam simulate-principal-policy, aws cloudtrail lookup-events, aws sts get-caller-identity...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an S3 Access Denied error (GetObject, PutObject, DeleteObject, ListBucket, HeadBucket), walking a symptom to the failing authorization layer with verify commands, validating why a role or user cannot access an object or bucket, or triaging a "cannot read from S3" incident where the root cause may be bucket policy, IAM policy, KMS, SCP, VPC endpoint, ownership, ACL, Block Public Access, Object Lock, presigned URL, cross-account, permission boundary, or Object Lambda access point — not necessarily the application code.
  when_not_to_use: S3 performance or latency optimisation (use s3-lifecycle-optimizer), S3 bucket creation (use s3-secure-bucket-deployer), S3 replication troubleshooting (use s3-replication-operator), or IAM policy authoring for least-privilege posture audits (use iam-least-privilege-advisor). This skill diagnoses Access Denied failures at access time; it does not audit steady-state security posture.
  activation_triggers: S3 AccessDenied, Access Denied S3, s3:GetObject AccessDenied, s3:PutObject AccessDenied, 403 Forbidden S3, bucket policy explicit deny, S3 cross-account access denied, S3 KMS AccessDenied, kms:DecryptObject denied, S3 VPC endpoint denied, presigned URL expired, S3 Object Lock denied, S3 Block Public Access, S3 object ownership denied, S3 permission boundary denied, SCP denying S3, S3 Object Lambda access denied, troubleshoot S3 access
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "application gets 403 on S3 GetObject"), optionally paired with the bucket name, key prefix, caller IAM principal, and CloudTrail event, OR (b) a bucket name plus caller context (IAM role ARN, source IP, VPC endpoint ID) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/ROOT_CAUSE/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and ROOT_CAUSE ∈ {EXPLICIT_DENY_BUCKET_POLICY, IMPLICIT_DENY_IAM, KMS_KEY_POLICY, SCP_DENY, VPC_ENDPOINT_POLICY, CROSS_ACCOUNT_MISSING_BUCKET_POLICY, OBJECT_OWNERSHIP, ACL_CONFLICT, BLOCK_PUBLIC_ACCESS, OBJECT_LOCK_RETENTION, PRESIGNED_URL_EXPIRED, PERMISSION_BOUNDARY, OBJECT_LAMBDA_ROUTING, REQUEST_ACCOUNT_MISMATCH, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "Application role arn:aws:iam::111111111111:role/app-role

    gets AccessDenied on s3:GetObject for

    s3://prod-data-bucket/orders/2024/order-001.json."

    Bucket: prod-data-bucket

    Key: orders/2024/order-001.json

    Caller: arn:aws:iam::111111111111:role/app-role

    Action: s3:GetObject

    Error: "Access Denied" (HTTP 403)

    CloudTrail eventSource: s3.amazonaws.com

    CloudTrail errorMessage: "Access Denied"

    KMS encryption: SSE-KMS with customer-managed key

    arn:aws:kms:us-east-1:111111111111:key/abc-123'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: S3, AccessDenied, bucket policy, IAM policy, explicit deny, object ownership, bucket owner enforcement, RequestAccount, KMS key policy, kms:DecryptObject, VPC endpoint policy, presigned URL, ACL, Block Public Access, Object Lock, cross-account, permission boundary, SCP, Object Lambda, access point, troubleshooting
  tags: s3, storage, troubleshooting, access-denied, iam-policy, bucket-policy, kms, vpc-endpoint, scp, object-lock
---

# S3 Access Denied Troubleshooter

## Quick start

- **Symptom → root-cause map (first plausible match drives the first probe):**
  AccessDenied on any S3 action → check the policy evaluation hierarchy:
  SCP (org level) → IAM identity policy → bucket policy → KMS key policy.
  An explicit Deny at ANY level overrides all Allow statements. If no
  explicit deny exists, check for an implicit deny (the action was never
  granted). Then check object ownership, VPC endpoint, presigned URL
  expiry, Block Public Access, Object Lock, and Object Lambda routing
  in that order.
- **Always verify with a probe, never guess.** Each root cause has a
  single command that proves or disproves it. A ROOT_CAUSE_IDENTIFIED
  verdict requires positive evidence — a failing probe that matches the
  symptom — not a process of elimination.
- **S3 auth evaluation = bucket policy AND IAM policy (explicit deny
  overrides allow) + KMS key policy is a separate gate + SCPs are
  checked first in the hierarchy.** If a customer-managed KMS key
  encrypts the object, the caller needs BOTH `s3:GetObject` AND
  `kms:Decrypt` (or `kms:DecryptObject` in the key policy). A missing
  KMS grant produces AccessDenied even when S3 policies are correct.
- **Cross-account access requires BOTH policies: the bucket policy in
  the bucket-owner account AND the IAM policy in the caller's account.**
  Same-account access works with either policy alone (the default
  evaluation allows if either grants). Cross-account needs both sides
  to explicitly allow — this is the #1 source of cross-account S3
  AccessDenied.
- **Object ownership determines who can read an object.** If the bucket
  owner is not the object uploader (pre-ObjectOwnership=BucketOwnerEnforced),
  the bucket owner's bucket policy cannot grant access to objects
  uploaded by another account — the uploader's ACLs control access.

## Mindset

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Mindset".
> Load when: framing where AccessDenied root causes live (policy chain vs non-policy gates)

## Philosophy

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Philosophy".
> Load when: explaining the four behaviours that separate senior S3 diagnosis from generalist guessing

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely root cause | First probe |
|---|---|---|
| `Access Denied`, `403 Forbidden` on any S3 API | Policy evaluation chain — start with SCP, then IAM, then bucket policy | `cloudtrail lookup-events` for the exact denied call; `iam simulate-principal-policy` |
| CloudTrail `errorMessage` contains "explicit deny" | EXPLICIT_DENY at some level | `simulate-principal-policy` returns `explicitDeny`; check SCP, bucket policy Deny statements, permission boundary |
| CloudTrail `errorMessage` is bare "Access Denied" (no "explicit deny") | IMPLICIT_DENY — the action was never granted | `simulate-principal-policy` returns `implicitDeny` |
| Caller has `s3:*` but SSE-KMS object still denied | KMS_KEY_POLICY — caller missing `kms:Decrypt` | `kms describe-key`, `kms get-key-policy`, `iam simulate-principal-policy --action-names kms:Decrypt` |
| Cross-account caller denied; same-account caller works | CROSS_ACCOUNT_MISSING_BUCKET_POLICY — bucket policy does not list the caller's account | `s3api get-bucket-policy` — check for a statement allowing the caller's principal |
| Objects uploaded by account B invisible to bucket owner (account A) | OBJECT_OWNERSHIP — ACLs control access, not bucket policy | `s3api get-object-acl` on a specific object; `s3api get-bucket-ownership-controls` |
| `x-amz-server-side-encryption` header present but AccessDenied | KMS key policy does not grant the caller | `kms get-key-policy`; key policy `Statement` for the caller principal |
| S3 access works from EC2 but not from VPC-attached Lambda/ECS | VPC_ENDPOINT_POLICY restricting S3 actions | `ec2 describe-vpc-endpoints` for the S3 Gateway endpoint policy |
| Presigned URL returns `AccessDenied` or `SignatureDoesNotMatch` | PRESIGNED_URL_EXPIRED — URL past expiry or signature region mismatch | Check `X-Amz-Expires`, `X-Amz-Date`, `X-Amz-Credential` in the URL |
| `s3:PutObject` denied only on objects with a legal hold or retention | OBJECT_LOCK_RETENTION — WORM mode prevents overwrite | `s3api get-object-retention`, `s3api get-object-legal-hold` |
| `s3:GetObject` denied on an Object Lambda access point ARN | OBJECT_LAMBDA_ROUTING — standard S3 ARN used instead of access point ARN | Check the ARN format: `arn:aws:s3-object-lambda:...` vs `arn:aws:s3:::...` |
| `403` on a bucket that worked yesterday with no policy change | SCP_DENY — a new SCP was attached at the org or OU level | `organizations list-policies-for-target` on the caller's account |
| STS assumed role works for some S3 actions but not others | PERMISSION_BOUNDARY — the permission boundary narrows effective permissions | `iam get-role` for `PermissionsBoundary`; `simulate-principal-policy` with `--permissions-boundary` |
| Bucket policy allows `s3:GetObject` but `NoSuchKey` or `AccessDenied` on specific objects | REQUEST_ACCOUNT_MISMATCH — bucket owner enforcement blocks non-owner requests | `s3api get-bucket-ownership-controls`; check if `BucketOwnerEnforced` is set |

## Pre-flight: gather the authorisation context

Before running root-cause-specific probes, gather the canonical
authorisation context and short-circuit on misconfigurations that
mimic AccessDenied.

### Account-wide pre-flight commands

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Pre-flight — account-wide commands".
> Load when: gathering caller identity, CloudTrail event, bucket policy, ownership, BPA, encryption, VPC endpoints before probing

### Caller-context short-circuit

| Finding | Effect on diagnosis |
|---|---|
| Caller is a role assumed via STS with a session policy | Session policies narrow effective permissions. Inspect `userIdentity.sessionContext` in CloudTrail. The session policy + IAM policy + bucket policy must all allow. |
| Caller is in a different AWS account than the bucket owner | Cross-account: BOTH the bucket policy and the caller's IAM policy must explicitly allow. Check both sides. |
| Caller is an IAM user with a permissions boundary | The permissions boundary acts as an additional filter. The effective permission = IAM policy AND permissions boundary. |
| The bucket has `BucketOwnerEnforced` (S3 Object Ownership) | ACLs are disabled. All objects are owned by the bucket owner. This eliminates ACL-based access control. |
| The caller is a service principal (e.g., `lambda.amazonaws.com`) | Service principals need `aws:SourceAccount` or `aws:SourceArn` conditions in the bucket policy for cross-service confused-deputy prevention. |

If the input is malformed (missing bucket name, absent error context,
no caller identity for live diagnosis), emit:

```text
TARGET: <bucket-name/key or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum the bucket
  name, the S3 action that was denied, and the caller's IAM principal
  ARN. For live diagnosis, also needed: the CloudTrail event for the
  denied call.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the bucket name and key
  prefix, (2) the exact S3 action (GetObject, PutObject, etc.) and
  the error message, and (3) the caller's IAM principal ARN or role
  name. For live diagnosis, also request the CloudTrail event JSON.
```

## Process — Diagnostic decision tree (apply in hierarchy order)

The diagnostic tree follows the S3 authorisation evaluation order.
Start at the top (SCPs) and work down to the non-policy gates. Each
root cause ends with either a positive confirmation (failing probe
that matches the symptom) or a pass that moves to the next check.
**Never emit ROOT_CAUSE_IDENTIFIED without a failing probe that
matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 0: Non-obvious behaviours that change diagnosis".
> Load when: interpreting an AccessDenied that does not match the obvious layer (KMS-vs-S3, deny hierarchy, cross-account consent, Object Lock, BPA, OLAP ARNs, SourceIp/VPCe, session filters)

### Step 1: Policy evaluation hierarchy — check SCPs first

Symptom: caller gets `Access Denied` on any S3 action. The first gate
in the evaluation hierarchy is the SCP layer at the Organizations
level.

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 1 — SCP layer probe commands".
> Load when: checking Step 1 (list/describe SCPs for the caller account)

Check each SCP for:
- A `Deny` statement with `Action: s3:*` or a specific `s3:GetObject`.
- A `Deny` with a `Condition` that matches the caller (e.g.,
  `StringNotEquals: aws:RequestedRegion`).
- A `Deny` that blocks specific KMS key ARNs (which transitively blocks
  S3 access to SSE-KMS objects).

If an SCP `Deny` matches the denied action and caller,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: SCP_DENY`.

### Step 2: IAM identity policy — check the caller's permissions

If no SCP denies, check the caller's IAM identity policies (managed +
inline). The IAM policy must `Allow` the specific S3 action on the
specific bucket ARN (or `*`).

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 2 — IAM simulation probe".
> Load when: checking Step 2 (simulate-principal-policy for the denied action)

`simulate-principal-policy` returns one of:
- `allowed` — the IAM policy allows the action. Move to Step 3.
- `implicitDeny` — no Allow statement exists for this action/resource.
  **ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: IMPLICIT_DENY_IAM`.
- `explicitDeny` — a Deny statement in the IAM policy or permission
  boundary matches. Check for `Deny` statements and the permissions
  boundary.

### Step 3: Permission boundary check

If the IAM policy allows but the caller still gets AccessDenied, check
for a permissions boundary on the role:

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 3 — permission boundary probes".
> Load when: checking Step 3 (get-role boundary + simulate with boundary)

If the simulation returns `explicitDeny` with the boundary,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: PERMISSION_BOUNDARY`.

### Step 4: Bucket policy — explicit deny and cross-account

If IAM allows and no permission boundary blocks, check the bucket
policy.

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 4 — bucket policy probe".
> Load when: checking Step 4 (get-bucket-policy for Deny / cross-account Allow)

Check for:
- A `Deny` statement matching the caller's principal, action, or
  source IP/VPCe. **ROOT_CAUSE_IDENTIFIED** with
  `ROOT_CAUSE: EXPLICIT_DENY_BUCKET_POLICY`.
- For cross-account callers: an `Allow` statement listing the caller's
  account ID or ARN. If missing, **ROOT_CAUSE_IDENTIFIED** with
  `ROOT_CAUSE: CROSS_ACCOUNT_MISSING_BUCKET_POLICY`.

### Step 5: KMS key policy — the separate gate

If the S3 policy chain allows, check whether the object is SSE-KMS
encrypted with a customer-managed key.

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 5 — KMS gate probes".
> Load when: checking Step 5 (bucket encryption, describe-key, get-key-policy, kms:Decrypt simulation)

If the caller lacks `kms:Decrypt` on the customer-managed key, or the
key policy does not grant the caller's account,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: KMS_KEY_POLICY`.

Note: if the object uses an AWS-managed key (`aws/s3`), the KMS key
policy is managed by AWS and cannot block the caller. If the caller
has `s3:GetObject`, the AWS-managed key decrypts transparently.

### Step 6: Object ownership — who owns the object?

If the policy chain and KMS all allow, check object ownership. This
applies when the bucket does NOT have `BucketOwnerEnforced` (i.e., the
bucket was created before April 2023 or explicitly set to
`ObjectWriter`).

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 6 — object ownership probes".
> Load when: checking Step 6 (ownership controls + object ACL)

If the ACL shows an owner that is NOT the bucket owner's account, and
the bucket policy does not account for the uploader's account, the
bucket owner cannot read the object via the bucket policy alone.
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: OBJECT_OWNERSHIP`.

Fix: enable `BucketOwnerEnforced` so all objects are owned by the
bucket owner. For existing objects, use S3 Batch Operations to copy
objects in-place (which changes ownership).

### Step 7: VPC endpoint policy

If the caller is VPC-attached (Lambda in VPC, ECS, EC2 in a VPC with
an S3 Gateway endpoint), check the endpoint policy.

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 7 — VPC endpoint policy probe".
> Load when: checking Step 7 (describe-vpc-endpoints for the S3 gateway policy)

A VPC endpoint policy can `Deny` specific S3 actions even when IAM
and bucket policy both allow. Test by bypassing the endpoint (route
via NAT Gateway) to confirm.

If the endpoint policy denies the action, **ROOT_CAUSE_IDENTIFIED**
with `ROOT_CAUSE: VPC_ENDPOINT_POLICY`.

### Step 8: Presigned URL validity

If the caller is using a presigned URL:

- Check `X-Amz-Expires` — the URL has a time limit. Default max is
  3600 seconds (1 hour) for IAM users; STS sessions can have longer.
- Check `X-Amz-Date` — the signing time.
- Check `X-Amz-Credential` — includes the region and signing date.
  A URL signed in `us-east-1` fails in `eu-west-1` with
  `SignatureDoesNotMatch`.
- Check `X-Amz-Signature` — if the signing credentials were rotated
  (access key deactivated), the signature is invalid.

If the URL is expired, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: PRESIGNED_URL_EXPIRED`.

### Step 9: Block Public Access

If the symptom is "public access blocked" despite a bucket policy
allowing `s3:GetObject` to `*`:

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 9 — Block Public Access probe".
> Load when: checking Step 9 (get-public-access-block)

Check all four settings:
- `BlockPublicAcls` — blocks new public ACLs.
- `IgnorePublicAcls` — ignores existing public ACLs.
- `BlockPublicPolicy` — blocks new public bucket policies.
- `RestrictPublicBuckets` — blocks public access via public bucket
  policies or ACLs.

If `RestrictPublicBuckets` is enabled and the bucket policy has a
public principal, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: BLOCK_PUBLIC_ACCESS`.

### Step 10: Object Lock retention

If the symptom is `AccessDenied` on `PutObject` or `DeleteObject` for
a specific object (not the whole bucket):

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 10 — Object Lock probes".
> Load when: checking Step 10 (lock configuration, retention, legal hold)

- `COMPLIANCE` mode: no principal (including root) can shorten the
  retention period or delete the object.
- `GOVERNANCE` mode: privileged users with
  `s3:BypassGovernanceRetention` can override.
- Legal hold: blocks deletion until explicitly removed.

If Object Lock is the cause, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: OBJECT_LOCK_RETENTION`.

### Step 11: S3 Object Lambda access point routing

If the caller is accessing an Object Lambda access point but using a
standard S3 ARN:

Check the ARN format in the caller's SDK call:
- Standard S3: `arn:aws:s3:::bucket/key`
- Object Lambda: `arn:aws:s3-object-lambda:<region>:<account>:accesspoint/<name>/key`

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 11 — Object Lambda probe".
> Load when: checking Step 11 (get-access-point-configuration-for-object-lambda)

If the caller used a standard S3 ARN but the policy is on the Object
Lambda access point, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: OBJECT_LAMBDA_ROUTING`.

### Step 12: Bucket owner enforcement (RequestAccount)

If the bucket has `BucketOwnerEnforced` and a cross-account caller
sends a request with `x-amz-expected-bucket-owner` that does not match:

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Step 12 — ownership controls probe".
> Load when: checking Step 12 (get-bucket-ownership-controls for RequestAccount mismatch)

If `BucketOwnerEnforced` is set and the caller does not include the
correct `x-amz-expected-bucket-owner` header (or includes the wrong
account ID), the request is rejected. **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: REQUEST_ACCOUNT_MISMATCH`.

## Output format

```text
TARGET: <bucket-name/key, caller-arn, action>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the root cause and the failing probe>
ROOT_CAUSE: <EXPLICIT_DENY_BUCKET_POLICY | IMPLICIT_DENY_IAM |
              KMS_KEY_POLICY | SCP_DENY | VPC_ENDPOINT_POLICY |
              CROSS_ACCOUNT_MISSING_BUCKET_POLICY | OBJECT_OWNERSHIP |
              ACL_CONFLICT | BLOCK_PUBLIC_ACCESS |
              OBJECT_LOCK_RETENTION | PRESIGNED_URL_EXPIRED |
              PERMISSION_BOUNDARY | OBJECT_LAMBDA_ROUTING |
              REQUEST_ACCOUNT_MISMATCH | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string, HTTP status, CloudTrail event>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <bucket> in <region>. Proceed?
  (yes/no)"
```

### Worked example — KMS key policy missing kms:Decrypt

```text
TARGET: s3://prod-data-bucket/orders/2024/order-001.json
  caller: arn:aws:iam::111111111111:role/app-role
  action: s3:GetObject
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Caller's IAM policy allows s3:GetObject on the bucket and the
  bucket policy allows the caller. However, the object is encrypted
  with a customer-managed KMS key
  (arn:aws:kms:us-east-1:111111111111:key/abc-123) and the caller's
  IAM policy does not include kms:Decrypt on the key ARN. The KMS
  gate is a separate authorisation layer from S3 (Step 5).
ROOT_CAUSE: KMS_KEY_POLICY
EVIDENCE:
  - Symptom: application role gets "Access Denied" (HTTP 403) on
    every s3:GetObject call for SSE-KMS objects in prod-data-bucket.
  - Probe: aws iam simulate-principal-policy on app-role for
    s3:GetObject returns "allowed".
  - Probe: aws s3api get-bucket-policy shows a statement allowing
    app-role to perform s3:GetObject.
  - Probe: aws iam simulate-principal-policy on app-role for
    kms:Decrypt on the key ARN returns "implicitDeny".
  - Passing: no SCP Deny for s3 or kms; no bucket policy Deny;
    no permission boundary on the role.
REMEDIATION:
  1. Add kms:Decrypt on the key ARN to the app-role IAM policy:
     aws iam put-role-policy --role-name app-role \
       --policy-name kms-decrypt-prod \
       --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"kms:Decrypt","Resource":"arn:aws:kms:us-east-1:111111111111:key/abc-123"}]}'
  2. Verify with simulate-principal-policy for kms:Decrypt.
  3. Re-test the application's s3:GetObject call.
CONFIRM: Before updating the role policy, emit and await:
  "CONFIRM: About to add kms:Decrypt on key abc-123 to role app-role.
   Proceed? (yes/no)"
```

### Worked example — Cross-account missing bucket policy

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Worked example — Cross-account missing bucket policy".
> Load when: emitting output for a cross-account caller blocked by the bucket policy

### Worked example — INSUFFICIENT_DATA

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Worked example — INSUFFICIENT_DATA".
> Load when: emitting output when bucket/action/caller context is missing

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.

- NEVER conclude the bucket policy is the problem without checking
  SCPs first. SCPs are evaluated before IAM and bucket policies. An
  SCP Deny on `s3:*` produces the same AccessDenied as a bucket
  policy Deny — but the fix is in the SCP, not the bucket policy.

- NEVER assume an AccessDenied on an SSE-KMS object is an S3-layer
  problem. The KMS key policy is a separate gate. Always check
  `kms:Decrypt` on the caller before concluding the S3 policy is
  wrong. The error string does not mention KMS.

- NEVER forget the permission boundary when the caller is an STS
  assumed role. The effective permission is IAM policy AND permission
  boundary AND session policy. A role with `s3:GetObject` in its IAM
  policy that also has a permission boundary scoping to a specific
  VPC will deny access from outside that VPC.

- NEVER grant `s3:*` on `*` as a fix. Root-cause diagnosis identifies
  the specific missing permission and the specific layer. Granting
  wildcard access masks the real issue and violates least-privilege.

- NEVER enable `BlockPublicPolicy` or `RestrictPublicBuckets` without
  understanding the impact. These settings silently block public
  bucket policies and public ACLs. A bucket that serves public
  content will start returning AccessDenied.

- NEVER delete an Object Lock retention configuration to "fix" an
  AccessDenied on delete. If the object is in COMPLIANCE mode, the
  retention cannot be bypassed. Check the mode before recommending
  a fix.

- NEVER use a standard S3 ARN for an Object Lambda access point. The
  Object Lambda service evaluates its own policy; the standard S3
  service never sees the request.

- NEVER assume `simulate-principal-policy` covers all conditions.
  The simulator does not evaluate VPC endpoint policies, bucket
  ACLs, or `aws:SourceIp` conditions for VPC-attached callers.
  Always cross-reference with the actual CloudTrail event for the
  denied call.

- NEVER conclude "the IAM policy is wrong" without checking whether
  the caller is an assumed role with a session policy. Session
  policies are ephemeral and do not appear in `get-role-policy`. The
  CloudTrail event's `userIdentity.sessionContext` is the only
  evidence of a session policy.

- NEVER assume presigned URL failures are IAM problems. An expired
  URL, a region mismatch in the signature, or rotated credentials
  all produce AccessDenied or SignatureDoesNotMatch — none of these
  are fixable by changing IAM policies.

- NEVER ignore the `x-amz-expected-bucket-owner` header. If the
  bucket has `BucketOwnerEnforced`, requests without the correct
  header (or with the wrong account ID) are rejected with
  AccessDenied.

## Pre-flight safety checks (run before any state-changing CLI)

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Pre-flight safety checks (run before any state-changing CLI)".
> Load when: about to emit or execute any state-changing remediation CLI (policy, boundary, BPA, ownership, retention)

## Remediation guidance

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Remediation guidance (per root cause)".
> Load when: emitting REMEDIATION for any identified ROOT_CAUSE

## Deep reference: S3 authorisation evaluation model

> **Moved verbatim** → [references/policy-evaluation-reference.md](references/policy-evaluation-reference.md) § "Deep reference: S3 authorisation evaluation model".
> Load when: explaining the full 10-layer hierarchy, explicit-vs-implicit deny signals, or the cross-account matrix

### KMS condition keys for S3

> **Moved verbatim** → [references/kms-and-ownership-reference.md](references/kms-and-ownership-reference.md) § "KMS condition keys for S3".
> Load when: scoping a KMS key policy to specific buckets (kms:ViaService, encryption context)

## Recent AWS features (2024-2026)

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features (2024-2026)".
> Load when: deciding whether a newer S3 feature changes the diagnosis

## References (load on demand)

- [references/policy-evaluation-reference.md](references/policy-evaluation-reference.md) — policy evaluation hierarchy and cross-account matrix, now also holding the deep-reference model moved from SKILL.md
- [references/kms-and-ownership-reference.md](references/kms-and-ownership-reference.md) — KMS key policy and ownership detail, now also holding the KMS condition keys for S3 moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — account-wide pre-flight commands, per-step probe CLIs, remediation guidance, pre-flight safety checks
- [references/worked-examples.md](references/worked-examples.md) — cross-account and INSUFFICIENT_DATA worked examples moved from SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset, philosophy, Step 0 non-obvious behaviours, recent AWS features

## Domain

AWS CloudOps / S3 Storage Access Control, IAM Policy Evaluation,
KMS Key Policy Integration, VPC Endpoint Policy, Organizations SCP
Hierarchy, and Object Lock Retention.

## AWS documentation

- **Amazon S3 User Guide — Bucket policy evaluation** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-evaluation.html
- **S3 bucket policies** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-iam-policies.html
- **S3 Object Ownership** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html
- **KMS key policies for S3** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html
- **S3 Block Public Access** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
- **S3 Object Lock** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- **VPC endpoint policies for S3** — https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html
- **IAM simulate-principal-policy** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_test-policies.html
- **AWS Organizations SCPs** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- **S3 Object Lambda access points** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/transforming-objects.html

