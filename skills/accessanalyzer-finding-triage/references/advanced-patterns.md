# Advanced Patterns — IAM Access Analyzer Finding Triage

Load-on-demand deep dives moved verbatim from SKILL.md: expert deltas, input schemas, classification detail, remediation playbooks, and recent features.

## Mindset — full triage framing

IAM Access Analyzer generates findings when a resource-based policy grants
access outside a defined **zone of trust**, or when an IAM identity (role,
user, access key, permission) is unused for a configurable analysis period.
The skill's job is not to restate what Access Analyzer already found — it is
to **triage** each finding into a risk verdict so the team knows what to fix
first, what to archive as expected, and what to dismiss as condition-bounded.

The critical insight: **not every Access Analyzer finding is a security
incident.** A KMS key policy granting `kms:Decrypt` to `config.amazonaws.com`
is a normal AWS service integration, not a data breach. An S3 bucket granting
`s3:PutObject` to another account with `aws:SourceArn` is cryptographically
bounded — the external account cannot misuse the access without the named
source resource. Conversely, a `Principal: "*"` grant with no condition is a
real public-exposure path regardless of how innocuous the resource seems.

## Quick triage — the three misclassification rules (detail)

1. **`isPublic: false` does NOT mean safe.** It only means the principal is not `"*"`. An external account principal with no condition is still EXTERNAL_ACCESS — the external account could be compromised.
2. **`Principal: "*"` + `aws:SourceArn` is SAFE**, not EXTERNAL_ACCESS. The source ARN is cryptographically validated at the AWS service layer — the external principal cannot forge it.
3. **Account vs Organization analyzer changes what is "external."** An account-scoped analyzer flags intra-org cross-account access; an org-scoped analyzer does not. The same finding can be EXPECTED (intra-org) or EXTERNAL_ACCESS (truly external) depending on analyzer scope.

## Expert knowledge deltas (non-obvious thresholds) — full catalog

### Delta 1: Access Analyzer does NOT evaluate identity-based policies

Access Analyzer only analyzes **resource-based policies** (bucket policies,
key policies, trust policies, etc.). It does NOT check whether the external
principal's identity-based policy actually grants the permission. This means:

- A finding may be flagged even if **no identity in the external account can
  actually exercise the access** — the resource policy allows it, but the
  external account has no IAM entity with the matching permission.
- Conversely, if the resource policy is permissive (`Principal: "*"`) but the
  external principal has no identity-based grant, the finding is still
  EXTERNAL_ACCESS because the risk is the resource policy, not the current
  identity state. An identity-based policy could be added at any time.
- **Triage implication:** never dismiss a finding because "the external
  account probably doesn't have the permission." The resource policy is the
  risk surface — triage based on what it grants, not on assumed identity
  state.

### Delta 2: The `isPublic` computation algorithm

Access Analyzer sets `isPublic: true` only when the effective principal
resolves to `"*"` AND no condition narrows the principal to a finite set.
Key nuances the docs do not state explicitly:

- `aws:SourceIp` does NOT flip `isPublic` to `false` — IP addresses are not
  principal-scoping conditions. A `Principal: "*"` with `aws:SourceIp:
  10.0.0.0/8` will still show `isPublic: true`.
- `aws:SourceArn` and `aws:SourceAccount` DO flip `isPublic` to `false`
  because they scope to a specific resource or account.
- `aws:Referer` and `aws:UserAgent` do NOT flip `isPublic` to `false` — they
  are forgeable and not treated as principal-scoping.
- If `isPublic` is `true`, the condition (if any) is not principal-scoping.
  The finding is public exposure regardless of what the condition appears to
  restrict.

### Delta 3: `StringEquals` vs `StringLike` on `aws:SourceArn`

The condition operator determines how much trust the SourceArn provides:

- `StringEquals` with a concrete ARN (`arn:aws:cloudtrail:us-east-1:999999999999:trail/my-trail`)
  → **Strongest.** Exact match required; no wildcard expansion.
- `StringLike` with a wildcard pattern (`arn:aws:cloudtrail:*:999999999999:*`)
  → **Strong but broader.** Still scoped to account 999999999999, but any
  region and any trail name in that account qualifies. SAFE for most cases,
  but note that a compromised service in the source account could generate
  requests from any region/trail.
- `StringLike` with account-level wildcard (`arn:aws:cloudtrail:*:*:*`)
  → **Weak.** Effectively no account scoping. Treat as NOT SAFE unless
  additional conditions narrow the scope.

### Delta 4: The `kms:CreateGrant` escalation chain

A cross-account KMS key policy granting `kms:Decrypt` is CRITICAL on its own,
but the hidden escalation vector is `kms:CreateGrant`. If the external
principal can call `kms:CreateGrant`, they can delegate decrypt access to
**any other principal** in their account — including IAM users, roles, or
even lambda functions they control. This turns a direct decrypt path into a
delegation surface.

- **Triage rule:** if the action set includes `kms:CreateGrant` for a
  cross-account principal, the risk is always **CRITICAL** regardless of
  other actions. The delegation capability makes the blast radius
  unbounded within the external account.
- If only `kms:Decrypt`/`kms:Encrypt` are granted (no `CreateGrant`), the
  blast radius is limited to principals in the external account that the
  external account admin chooses to enable — still CRITICAL for KMS, but the
  delegation chain is shorter.

### Delta 5: Unused-access analysis period is configurable (not fixed at 90 days)

The default unused-access analysis period is 90 days, but it is configurable
to 30, 60, or 90 days via the analyzer configuration. Key implications:

- A role flagged as `UnusedIAMRole` with a 90-day period may have been used
  91 days ago — it is stale but not necessarily abandoned.
- A quarterly batch job (runs every 91+ days) will always show as unused in
  a 90-day window. Query CloudTrail for the actual last-accessed timestamp
  before recommending deletion.
- If the analysis period is set to 30 days, the noise volume increases
  significantly — more roles will appear "unused" that are simply
  infrequently used.

### Delta 6: The `analyzedAt` staleness threshold

Access Analyzer re-analyzes resources when the resource policy changes. But
the `analyzedAt` timestamp on a finding reflects when the analysis was last
performed, not when the policy last changed. Expert thresholds:

- **< 24 hours:** fresh — act on the finding as-is.
- **24 hours to 7 days:** stale — re-run `aws accessanalyzer list-findings`
  before acting. The policy may have changed since the analysis.
- **> 7 days:** very stale — the finding may already be resolved. Always
  re-run before any remediation action.

### Delta 7: `aws:PrincipalAccount` is deprecated — use `aws:SourceAccount`

Older policies may use `aws:PrincipalAccount` in conditions. This key is
deprecated and should not be treated as equivalent to `aws:SourceAccount`:
- `aws:SourceAccount` is evaluated at the service layer and cannot be forged.
- `aws:PrincipalAccount` may not be present in all request contexts and its
  semantics vary by service.
- If a finding's condition uses `aws:PrincipalAccount`, classify as
  EXPECTED (not SAFE) and note that the condition key should be migrated to
  `aws:SourceAccount`.

### Delta 8: Organization analyzer delegated administrator model

For organization-scoped analyzers, the analyzer is created in a **delegated
administrator account** (not the management account). Archive rules for
org-level findings must be created in the delegated administrator account.
This matters for triage:

- If you are triaging from the member account perspective, you cannot create
  archive rules for org-level findings — you must escalate to the delegated
  administrator.
- The REMEDIATION output should note which account can archive the finding
  based on the analyzer type.

## Zone of trust model — analyzer type table

| Analyzer type | Zone of trust | What is "external" |
|---|---|---|
| **Account** (`TYPE: ACCOUNT`) | The analyzer's AWS account only | Any principal in a different account — **including accounts in the same AWS Organization**. Cross-account access within the org IS flagged. |
| **Organization** (`TYPE: ORGANIZATION`) | The entire AWS Organization | Only principals outside the org. Cross-account access within the org is NOT flagged. |

## Zone of trust model — triage implication

**Triage implication:** when evaluating a finding, know which analyzer type
generated it. If an account-scoped analyzer flags access from another account
in the same org, that finding may be EXPECTED (intra-org integration) even
though the principal is technically "external" to the analyzer's zone. The
finding is valid per the analyzer's scope, but the risk is lower because the
principal is within the org's governance boundary.

## Finding types — input schemas and catalogs

### External access findings (`findingType: ExternalAccess`)

Generated when a **resource-based policy** grants access to a principal
outside the zone of trust. Resource-based policies include:

- S3 bucket policies, S3 access-point policies
- KMS key policies
- SQS queue policies, SNS topic policies
- Secrets Manager secret policies
- IAM role trust policies (the `AssumeRolePolicyDocument`)
- Lambda function policies, Lambda layer policies
- EFS file-system policies
- EventBridge event-bus policies
- AWS Backup vault policies
- OpenSearch domain policies
- Glue Data Catalog resource policies

Each external-access finding includes:
- `principal` — the external principal ARN, `"*"`, or a structured principal
  (`{"AWS": ...}`, `{"Service": ...}`, `{"Federated": ...}`)
- `isPublic` — boolean, pre-computed by Access Analyzer. `true` when the
  effective principal is `"*"` (or resolves to all principals) and no
  principal-scoping condition narrows it. See Delta 2 for the exact
  algorithm.
- `condition` — flattened map of condition key-value pairs from the policy
  statement that triggered the finding (not the full IAM condition block)
- `action` — list of IAM actions granted to the external principal
- `resourceType` — the AWS resource type (e.g., `AWS::S3::Bucket`)

### Unused access findings

Generated by **IAM Access Analyzer unused-access analysis** (a separate
analyzer configuration). Identifies IAM entities that have not been used
within the analysis period (default 90 days, configurable to 30/60/90):

| Finding type | What it means |
|---|---|
| `UnusedIAMRole` | Role not used by any service or principal in the analysis period |
| `UnusedIAMUserAccessKey` | An access key that has not been used for API calls |
| `UnusedIAMUserPassword` | Console password not used for login in the analysis period |
| `UnusedIAMPermission` | Specific IAM actions in a policy that have not been exercised |
| `UnusedServiceControlPolicy` | An SCP that does not affect any account in the org |

## Step 0 — field requirement table

Verify the finding has the minimum fields required for triage. This is
not generic validation — each field gates a specific classification branch:

| Field | Required for | If missing |
|---|---|---|
| `findingType` | Routing (Step 1A vs 1B) | ERROR — cannot determine classification path |
| `status` | Step 1A.1 / 1B.1 (status check) | Assume ACTIVE (safer default) |
| `principal` | Step 1A.4 (principal classification) | For ExternalAccess: ERROR — cannot classify without principal |
| `condition` | Step 1A.2 (condition strength) | Treat as `{}` (absent condition) |
| `isPublic` | Step 1A.5 (severity escalation) | Infer from principal (`"*"` → `true`) |
| `action` / `actions` | Step 1A.5 (risk level) | If missing, assume worst-case for the resource type |
| `resourceType` | Step 1A.5 (severity matrix) | If missing, infer from resource ARN or flag as AMBIGUOUS |

## Step 1A.2 — condition strength categories (full detail)

Examine the `condition` field. Classify the condition strength using the
**Condition strength matrix** below. This is the primary differentiator
between EXTERNAL_ACCESS, SAFE, and EXPECTED:

**CRYPTOGRAPHIC conditions → SAFE (Step 1A.3):**
- `aws:SourceArn` with a **specific concrete ARN** using `StringEquals` (not
  a wildcard pattern) — the access is cryptographically bound to the named
  resource. AWS validates the source resource at the service layer; the
  external principal cannot forge it. This is the strongest possible
  restriction. See Delta 3 for operator semantics.
- `aws:SourceArn` with a wildcard pattern (e.g.,
  `arn:aws:cloudtrail:*:999999999999:*`) using `StringLike` — still STRONG
  but scoped to the account. Classify as SAFE with a note that wildcard ARN
  patterns are broader than concrete ARNs (a compromised service in the
  source account could generate requests from any region).

**ACCOUNT-SCOPED conditions → SAFE (Step 1A.3):**
- `aws:SourceAccount` with a specific account ID — the request must originate
  from the named account. Cannot be forged. If the account is a known partner
  or member of the same org, this is SAFE. If the account is unknown, this is
  still technically bounded but should be flagged for identity verification —
  downgrade to EXPECTED with a note.
- **Deprecated:** `aws:PrincipalAccount` (see Delta 7) — classify as EXPECTED,
  not SAFE, and note the condition key should be migrated.

**ORGANIZATION-SCOPED conditions → SAFE:**
- `aws:PrincipalOrgID` with the org ID — restricts to principals within the
  named AWS Organization. SAFE if the org is your own; AMBIGUOUS if the org is
  a third-party org.

**NETWORK-SCOPED conditions → SAFE for private, AMBIGUOUS for public:**
- `aws:SourceVpce` (VPC Endpoint ID) — request must traverse the named
  endpoint. Cannot be forged by external callers.
- `aws:SourceVpc` (VPC ID) — request must originate in the named VPC.
- If the VPC/VPCe has internet gateway routes, the network scoping is weaker
  (an attacker inside the VPC could relay). Still SAFE for most practical
  purposes, but note the assumption.
- **`aws:SourceIp` does NOT flip `isPublic` to false** (see Delta 2). IP
  conditions are not principal-scoping. Evaluate separately: RFC1918 CIDR
  without IGW route → SAFE; `0.0.0.0/0` → NOT SAFE (equivalent to no
  condition); public CIDR → AMBIGUOUS.

**SERVICE-COUPLED conditions → SAFE:**
- `kms:ViaService` — KMS access only through a named AWS service (e.g.,
  `kms:ViaService: "s3.us-east-1.amazonaws.com"`). The caller cannot decrypt
  directly; they must go through the named service. Note: this is weaker than
  `aws:SourceArn` because the caller still controls which service they route
  through, but the named service enforces its own access controls.

**WEAK / FORGEABLE conditions → NOT SAFE (treat as no condition):**
- `aws:Referer` — client-supplied HTTP header, trivially forgeable by any HTTP
  client. Provides zero access control.
- `aws:UserAgent` — same; forgeable client-side.
- Any condition wrapped only in `IfExists` — weakens the assertion to
  "evaluate if present, ignore if absent." Treat per the underlying key but
  flag the `IfExists` semantics.
- `aws:SourceArn` with `StringLike` and account-level wildcard
  (`arn:aws:s3:*:*:*`) — effectively no account scoping.

**ABSENT condition → NOT SAFE:**
- If `condition` is `{}` or missing, the access is unconditional. Proceed to
  Step 1A.4.

## Step 1A.4 — AWS service principal (detail)

- Check the **Expected service integrations** table below. If the service
  principal matches a known integration pattern for the resource type, output
  EXPECTED.
- Service principals in role trust policies (e.g.,
  `lambda.amazonaws.com`, `ecs-tasks.amazonaws.com`, `ec2.amazonaws.com`)
  are the standard pattern for service execution roles → EXPECTED.
- Service principals in KMS/S3 resource policies (e.g.,
  `config.amazonaws.com`, `cloudtrail.amazonaws.com`, `logging.amazonaws.com`)
  are standard service-to-resource integrations → EXPECTED.
- **Exception:** if the service principal grants broad destructive actions
  (e.g., `s3:DeleteObject` to a generic service principal, or
  `iam:PutRolePolicy` to an unexpected service), flag as EXTERNAL_ACCESS with
  a note that the service principal pattern is unusual.

## Step 1A.4 — federated principal (detail)

- A federation integration (Okta, Azure AD, GitHub OIDC). If the identity
  provider is in the same account, this is an internal federation path →
  EXPECTED. If the IdP is in an external account → EXTERNAL_ACCESS (unusual
  and high-risk: external IdP control over role assumption).

## Step 1A.4 — specific external account principal (detail)

- No condition, external account, resource policy grants access →
  EXTERNAL_ACCESS. The risk level depends on the resource type and actions
  (Step 1A.5).
- **Exception:** if the input includes context that the external account is a
  known CI/CD deployment account, monitoring account, or documented SaaS
  partner, classify as EXPECTED with a note to create an archive rule.

## Step 1A.4 — public principal (detail)

- No restrictive condition + public principal → EXTERNAL_ACCESS. The risk
  level depends on the resource type and actions (Step 1A.5). If `isPublic`
  is `true`, the finding is confirmed public by Access Analyzer.

## Step 1A.5 — severity escalation rules (full detail)

- If `isPublic` is `true` AND the resource type is KMS, Secrets Manager, or
  S3 with write actions, this is **incident-response priority** — flag the
  REMEDIATION as "IMMEDIATE."
- For specific external account principals (not public), downgrade by one
  level from the matrix (CRITICAL → HIGH, HIGH → MODERATE) because the
  exposure is to one account, not the entire internet — unless the actions
  are admin/trust (stays CRITICAL).
- **KMS escalation chain (Delta 4):** if the action set includes
  `kms:CreateGrant` for a cross-account principal, risk is always
  **CRITICAL** regardless of other actions — the delegation capability
  makes the blast radius unbounded within the external account.

## Step 1A.6 — expected service integrations table

| Service principal | Resource type | Expected actions | Integration |
|---|---|---|---|
| `cloudtrail.amazonaws.com` | S3 Bucket | `s3:GetBucketAcl`, `s3:PutObject` | CloudTrail log delivery |
| `logging.amazonaws.com` | S3 Bucket | `s3:PutObject` | S3 server access log delivery |
| `config.amazonaws.com` | S3 Bucket, KMS Key | `s3:GetBucketAcl`, `s3:PutObject`, `kms:Decrypt`, `kms:GenerateDataKey` | AWS Config configuration recording |
| `config-multiaccountsetup.amazonaws.com` | IAM Role | `sts:AssumeRole` | Config multi-account aggregator |
| `lambda.amazonaws.com` | IAM Role | `sts:AssumeRole` | Lambda execution role |
| `ecs-tasks.amazonaws.com` | IAM Role | `sts:AssumeRole` | ECS task execution role |
| `ec2.amazonaws.com` | IAM Role | `sts:AssumeRole` | EC2 instance profile |
| `ssm.amazonaws.com` | IAM Role | `sts:AssumeRole` | Systems Manager managed instance |
| `backup.amazonaws.com` | KMS Key, Backup Vault | `kms:Decrypt`, `kms:Encrypt`, `backup:*` | AWS Backup service |
| `elasticloadbalancing.amazonaws.com` | S3 Bucket | `s3:PutObject` | ALB/NLB access log delivery |
| `sns.amazonaws.com` | S3 Bucket | `s3:PutObject` | S3 event notification delivery |
| `sqs.amazonaws.com` | S3 Bucket | `s3:PutObject` | S3 event notification delivery |
| `events.amazonaws.com` | SNS Topic, SQS Queue, EventBridge | `sns:Publish`, `sqs:SendMessage`, `events:PutEvents` | EventBridge rule target delivery |
| `delivery.logs.amazonaws.com` | S3 Bucket | `s3:PutObject` | CloudWatch Logs delivery to S3 |
| `athena.amazonaws.com` | S3 Bucket | `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` | Athena query results read/write |
| `states.amazonaws.com` | Lambda, SNS, SQS | `lambda:InvokeFunction`, `sns:Publish`, `sqs:SendMessage` | Step Functions service integration |
| `guardduty.amazonaws.com` | S3 Bucket, KMS Key | `s3:PutObject`, `kms:GenerateDataKey` | GuardDuty finding export |
| `securityhub.amazonaws.com` | S3 Bucket | `s3:PutObject` | Security Hub finding export |
| `firehose.amazonaws.com` | S3 Bucket | `s3:PutObject` | Kinesis Firehose delivery |
| `vpn.amazonaws.com` | S3 Bucket | `s3:GetObject` | Client VPN endpoint configuration |

## Step 1B.2 — risk rationale (unused access key)

- An unused access key is a **credential-theft vector** — it provides
  programmatic API access with no MFA requirement. If exfiltrated (e.g.,
  from a CI config, committed `.aws/credentials`, or a compromised
  developer machine), the attacker has silent API access.
- Risk is always **HIGH** for unused access keys, regardless of the user's
  attached policies. Even a read-only user's unused key is HIGH because the
  key itself is the risk (it's a static credential sitting dormant).

## Step 1B.2 — risk rationale (unused console password)

- An unused console password is lower risk than an access key because console
  access typically requires MFA (if configured). But if MFA is not enforced,
  the password alone is a console access path.

## Step 1B.2 — risk rationale (unused role)

- A role unused for 90+ days is a **credential-hygiene risk** — stale
  identities expand the attack surface. If the role's credentials (temporary
  session tokens) were obtained and cached before the role became unused, they
  could still be valid.

## Step 1B.2 — risk rationale (unused permission)

- Individual unused actions within a policy are a **scoping opportunity**, not
  an active vulnerability. The actions are not exercised, so they can be
  removed without impact (after validation).

## Step 1B.3 — expected-unused patterns

Certain unused entities are **intentionally unused** and should be classified
as EXPECTED:

- **Service-linked roles** (role name contains `/service-role/` or the path
  includes `aws-service-role`) — these are managed by AWS services and should
  NOT be deleted even if unused. They will be recreated when the service
  needs them. → EXPECTED with note "service-linked role — do not delete."

- **Break-glass / emergency-access roles** — if the input includes context
  that the role is a documented emergency-access role (name contains
  `break-glass`, `emergency`, `incident-response`, `dr-`), classify as
  EXPECTED with note "break-glass role — expected to be unused; verify access
  logging is enabled."

- **Cross-account audit roles** — roles assumed by a security or audit tool
  account for periodic compliance scans. These may be used infrequently
  (monthly/quarterly) and may appear unused in a 90-day window. → EXPECTED
  with note to extend the analysis period or add the role to an exclusion
  list.

- **AWS-managed job-function roles** (e.g., `AWSBatchServiceRole`,
  `AWSServiceRoleFor*`) — these are service-managed and should not be
  modified. → EXPECTED.

## Pre-flight — prefer additive changes

- **Prefer additive changes** (adding a Deny statement, adding a condition)
  over destructive changes (removing a statement, deleting a policy). A Deny
  is reversible by removing the Deny; a removed Allow may lose the intent
  that originally created the grant.

## Pre-flight — public-write incident response

- **For public-write findings (EXTERNAL_ACCESS / CRITICAL on S3, EFS, Backup
  Vault), treat as incident response.** The fastest containment is usually a
  broad Deny statement (`"Effect": "Deny", "Principal": "*", "Action": "*",
  "Resource": "<arn>"`) or removing the public statement — do this BEFORE
  full forensic capture, because every second of public-write exposure is
  data destruction risk. Capture state AFTER containing. This is the ONE
  exception to the "capture before modify" rule — for active public-write
  exposure, containment is higher priority than backup.

## Pre-flight — deactivate (not delete) access keys

- **For unused access keys, deactivate (not delete) first.** `aws iam
  update-access-key --access-key-id <id> --status Inactive` is reversible.
  Delete only after confirming no workload breaks (1-2 week observation
  period via CloudTrail).

## Remediation — EXTERNAL_ACCESS (public, no condition)

1. **Immediate containment:** add a Deny-all statement or restrict the
   principal to specific internal ARNs. For S3, enable Block Public Access
   (BPA) at bucket level — this is the fastest containment.
2. **Root-cause the policy:** identify who created the public grant and why.
   Often it was a debugging shortcut (`Principal: "*"` to test access) that
   was never removed.
3. **If cross-account access is legitimately needed:** replace `Principal:
   "*"` with the specific external account ARN and add `aws:SourceAccount`
   or `aws:SourceArn` condition.
4. **Audit CloudTrail** for the exposure window: check for unauthorized
   `GetObject`, `PutObject`, `Decrypt`, or `AssumeRole` events from
   principals outside your account during the period the policy was public.
5. **Check for `kms:CreateGrant` in the action set** (Delta 4) — if present,
   the external account may have created delegation grants. Audit
   ` kms:CreateGrant` events and revoke any unauthorized grants:
   `aws kms list-grants --key-id <key-id>`.

## Remediation — EXTERNAL_ACCESS (specific external account)

1. **Verify the external account is known.** Check with the application owner
   whether the external account is a partner, CI/CD pipeline, or monitoring
   tool.
2. If known → classify as EXPECTED and create an archive rule to suppress
   future instances: filter on the principal ARN + resource type + actions.
3. If unknown → restrict immediately. Remove the external account from the
   resource policy and monitor CloudTrail for any legitimate access that
   breaks.
4. **If the access must remain,** add a condition (`aws:SourceAccount` or
   `aws:SourceArn`) to bound it cryptographically, then downgrade to SAFE.

## Remediation — UNUSED_ACCESS (unused role)

1. **Validate non-use:** query CloudTrail for any `AssumeRole` events on the
   role ARN in the last 30-90 days. Access Analyzer's 90-day window may miss
   quarterly batch jobs — extend the query if needed.
2. **If confirmed unused:** detach all managed policies, delete inline
   policies, then delete the role. Capture the role configuration first:
   `aws iam get-role --role-name <name> > /tmp/<name>-backup.json`.
3. **If still needed but over-permissioned:** generate a scoped policy from
   CloudTrail activity (same workflow as `iam-least-privilege-advisor`) and
   replace the existing policy.
4. **For service-linked roles:** do NOT delete. Classify as EXPECTED.

## Remediation — UNUSED_ACCESS (unused access key)

1. **Deactivate immediately** (not delete): `aws iam update-access-key
   --access-key-id <id> --status Inactive --user-name <name>`. This is
   reversible and stops the credential-theft vector.
2. **Audit CloudTrail** for any API calls using this key in the last 90 days.
   If the key was used by an unknown source, treat as a potential compromise
   — rotate all credentials for the user and investigate.
3. **After 1-2 weeks of no breakage,** delete the key: `aws iam
   delete-access-key --access-key-id <id> --user-name <name>`.

## Remediation — EXPECTED

1. **Create an archive rule** to suppress future instances of the same
   pattern. The archive rule should filter on the principal, resource type,
   and condition that identify the expected integration.
2. **Document the justification:** integration name, owner, ticket reference.
3. **Periodically review** archived findings (quarterly) to verify the
   integration is still active and the external principal has not been
   compromised.

## Remediation — SAFE

1. No remediation required. The condition bounds the access.
2. Optionally create an archive rule to suppress future instances of
   condition-bounded findings on the same resource type.
3. Note the condition in the finding's archive comment for future auditors.

## Archive-rule patterns (template, scoping, common patterns)

```json
{
  "filter": {
    "resourceType": {"eq": ["AWS::S3::Bucket"]},
    "principal": {"contains": ["cloudtrail.amazonaws.com"]},
    "action": {"contains": ["s3:PutObject"]}
  }
}
```

Archive rules are analyzer-scoped — they apply to one analyzer. For
organization analyzers, create archive rules at the delegated administrator
account level (see Delta 8). For account analyzers, create archive rules
in the account that owns the analyzer.

**Common archive-rule patterns:**
- AWS service log delivery (CloudTrail, Config, ELB, S3 access logs)
- Cross-account CI/CD deployment roles (filter on the CI/CD account principal
  + `sts:AssumeRole`)
- KMS key decrypt for known data-lake consumer accounts (filter on
  `kms:Decrypt` + `aws:SourceAccount`)
- SNS/SQS cross-account event delivery (filter on the monitoring account
  principal)

## Recent AWS features (2024-2026)

- **Unused-access analysis GA (2024):** UnusedIAMRole, UnusedIAMUserAccessKey, UnusedIAMPermission, and UnusedServiceControlPolicy finding types are now GA for account and organization analyzers. The skill already covers these, but auditors should expect a higher volume of unused-access findings now that the feature is enabled by default on new analyzers.
- **New supported resource types:** Access Analyzer now evaluates resource-based policies for S3 directory buckets (`AWS::S3Express::DirectoryBucket`), VPC endpoints (`AWS::EC2::VPCE`), and CloudWatch Logs resource policies. Findings from these new types flow through the same triage logic — ensure archive rules account for them.
- **External-access analyzer for KMS and Secrets Manager:** expanded coverage means more granular findings for KMS key grants and Secrets Manager resource policies. The Delta 4 (kms:CreateGrant escalation) logic applies to these new finding shapes.
- **Organization-level analyzer enhancements:** delegated administrator can now manage archive rules across the org centrally, and unused-access findings include `UnusedServiceControlPolicy` which affects SCP audit posture.

## Related skills — companion-skill detail

- **`iam-least-privilege-advisor`** — classifies identity-based IAM policies
  for wildcard and escalation risk. Use after remediating an unused-access
  finding to scope down the replacement policy.
- **`s3-public-access-auditor`** — audits S3 bucket configurations for public
  access. Complements this skill's S3 external-access finding triage with
  BPA/ACL-level analysis.
