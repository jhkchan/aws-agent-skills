# SCP Evaluation and Inheritance Reference

Load this reference when planning or executing any SCP deployment that
spans multiple hierarchy levels. The procedures below are the canonical
evaluation model for AWS Organizations, with hierarchy traversal,
intersection rules, and edge-case handling.

## SCP evaluation model

### The intersection rule (single most important fact)

For any API call made by a principal in a member account, the
effective permission set is the intersection of:

1. Every SCP attached at the org root.
2. Every SCP attached at each OU in the path from root to the account.
3. Every SCP attached directly to the account.

The call is permitted at the Organizations layer ONLY if AT LEAST ONE
SCP at EVERY level of the hierarchy contains an `Allow` statement for
the action (or does not explicitly `Deny` it). The principal's IAM
identity policy is then evaluated separately.

```
Effective = IAM policy ∩ SCP_root ∩ SCP_parent_OU ∩ SCP_child_OU ∩ SCP_account
```

A `Deny` anywhere in the chain blocks the call. An `Allow` is required
at every level (or implicit allow from `FullAWSAccess`).

### What SCPs do NOT do

- **Do not grant permissions.** An `Allow` in an SCP only permits the
  IAM layer to grant that action. The principal still needs an IAM
  identity policy.
- **Do not apply to the management account.** The management account
  is exempt. Harden it separately.
- **Do not affect service-linked roles in all cases.** Some
  service-linked roles (e.g., `AWSServiceRoleForOrganizations`) are
  exempt from SCP filtering.
- **Do not apply to principals outside the organization.**
  Cross-account resource-based policies grant access to external
  principals without filtering through the org member account's SCPs
  in certain cases (verify with IAM Access Analyzer).

## Inheritance traversal

### Root → OU → child OU → account

For an account at `ou-prod-a → ou-prod-app-1 → 111111111111`:

| Level | SCPs attached |
|---|---|
| Root | `FullAWSAccess`, `deny-regions`, `deny-root-user` |
| `ou-prod-a` | `require-encryption`, `cap-ec2-instances` |
| `ou-prod-app-1` | `deny-iam-user-create` |
| `111111111111` | (none) |

Effective: `FullAWSAccess` AND all four custom SCPs intersected. The
most restrictive condition wins. A `Deny` at root propagates to every
descendant unconditionally.

### What does NOT propagate

- Account-level SCPs do NOT propagate to other accounts.
- Tag policies do NOT inherit by tag value — they inherit by OU
  hierarchy.
- Backup policies and AI services opt-out policies follow the same
  hierarchy model as SCPs.

## Condition key cheat sheet

| Key | Use case |
|---|---|
| `aws:RequestedRegion` | Allowlist approved regions |
| `aws:PrincipalType` | Target root user (`root`), assumed-role (`assumed-role`), etc. |
| `aws:PrincipalArn` | Target specific principals |
| `aws:PrincipalTag/<key>` | Tag-based scoping (principal must have the tag) |
| `aws:PrincipalAccount` | Account-level scoping |
| `aws:CalledVia` | Chained-service scoping (list of service names) |
| `aws:CalledViaFirst` | First service in the chain |
| `aws:CalledViaLast` | Last service in the chain |
| `aws:RequestTag/<key>` | Require tags on create/update calls |
| `aws:ResourceTag/<key>` | Scope by tag on the resource being acted on |
| `aws:MultiFactorAuthPresent` | Require MFA for sensitive actions |
| `aws:SourceIp` | CIDR scoping (use with care — breaks chained calls) |
| `s3:x-amz-server-side-encryption` | Require SSE-KMS on S3 PutObject |
| `ec2:InstanceType` | Restrict EC2 instance families |
| `ec2:Attribute` | Restrict EC2 attributes |

## Validation workflow

1. Author the SCP JSON locally.
2. `aws accessanalyzer validate-policy --policy-document file://scp.json
   --policy-type RESOURCE_POLICY` — catches syntax errors.
3. `aws organizations create-policy --content file://scp.json ...` —
   AWS rejects malformed policies at this step.
4. Attach to a non-production OU first (sandbox or staging).
5. Verify with `list-policies-for-target` and an IAM Access Analyzer
   effective-permissions query (if configured).
6. Promote to production root only after staging validation.

## Self-lockout recovery procedure

If an SCP locks every member account:

1. Authenticate as the management account (it is exempt).
2. List the offending policy:
   `aws organizations list-policies-for-target --target-id <root-id>
   --filter SERVICE_CONTROL_POLICY`
3. Detach immediately:
   `aws organizations detach-policy --policy-id <policy-id>
   --target-id <root-id>`
4. Re-author with narrower scope before re-attaching.

Time-to-recover is seconds once management-account credentials are
available. The operational risk is having those credentials available
under break-glass — pre-provision them.
