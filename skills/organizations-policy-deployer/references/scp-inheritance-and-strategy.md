# SCP Inheritance and Strategy — Organizations Policy Deployer

Deep reference on SCP inheritance (intersection mechanics, OU chain
evaluation, effective-SCP computation), Allow list vs Deny list
strategy (when to use each, the FullAWSAccess detach sequencing,
and per-entity conflict rules), and break-glass exception patterns.
Loaded on demand by the skill — kept out of the main SKILL.md body
so the deployment procedure stays scannable.

## SCP inheritance fundamentals

### Inheritance is intersection

At any entity (root, OU, or account), the EFFECTIVE SCP is the
intersection of every SCP attached along the chain from root down
to that entity. An action passes the SCP filter only if EVERY SCP
along the chain ALLOWS it (or does not address it). An explicit
Deny in ANY SCP along the chain wins — the action fails.

```text
Effective SCP at entity E =
  ALLOWED = ⋂ (Allow sets of every SCP attached along the chain root → E)
  DENIED  = ⋃ (explicit Deny statements along the chain root → E)
  Result  = ALLOWED − DENIED
```

### Worked example — three-level intersection

```text
Root [SCP_R]
  Allow: ec2:*, s3:*, iam:*, rds:*
  Deny:  iam:DeleteRole

  └── OU_Apps [SCP_A]
        Allow: ec2:*, s3:*
        (no Denies)

        └── Account 1111 [SCP_ACCT]
              Allow: ec2:RunInstances, ec2:Describe*
              Deny:  ec2:TerminateInstances (break-glass carve-out)

Effective SCP at Account 1111:
  ALLOWED = {ec2:*, s3:*, iam:*, rds:*}            (root)
          ⋂ {ec2:*, s3:*}                          (OU_Apps)
          ⋂ {ec2:RunInstances, ec2:Describe*}      (account)
          = {ec2:RunInstances, ec2:Describe*}

  DENIED  = {iam:DeleteRole}                       (root)
          ⋃ {ec2:TerminateInstances}               (account)
          = {iam:DeleteRole, ec2:TerminateInstances}

  Net ALLOWED at 1111 = {ec2:RunInstances, ec2:Describe*}
  Net DENIED  at 1111 = {iam:DeleteRole, ec2:TerminateInstances}
```

Notice that `s3:*` and `iam:*` were ALLOWED at the root and OU
but DROPPED at the account level because the account SCP did NOT
include them in its Allow set. The intersection removes them.

### Trace the chain with the CLI

```bash
# Start at the target entity and walk parents
TARGET=111122223311

while [ -n "$TARGET" ]; do
  echo "=== $TARGET ==="
  aws organizations list-policies-for-target \
    --target-id "$TARGET" \
    --filter SERVICE_CONTROL_POLICY \
    --query 'Policies[*].{Name:Name,Id:Id,AwsManaged:AwsManaged}' \
    --output table

  # Walk up
  PARENT=$(aws organizations list-parents \
    --child-id "$TARGET" \
    --query 'Parents[0]' --output json)
  TYPE=$(echo "$PARENT" | jq -r '.Type')
  TARGET=$(echo "$PARENT" | jq -r '.Id')
  [ "$TYPE" = "ORGANIZATION" ] && break
done
```

### Common inheritance pitfalls

1. **Assuming root Allow propagates.** It does NOT propagate
   unless EVERY child also Allows. A child OU SCP that omits a
   service removes that service from the intersection.

2. **Forgetting that the management account is exempt.** SCPs
   never affect the management (payer) account, regardless of
   what is attached at root. Use IAM and break-glass procedures
   to constrain the management account.

3. **Mixing Allow-list and Deny-list at the same entity.** If
   `FullAWSAccess` remains attached alongside an Allow-list SCP,
   the Allow-list is silently redundant — the intersection
   includes everything `FullAWSAccess` permits.

4. **Treating `Resource: *` as scope-limiting.** SCPs ignore the
   `Resource` element entirely. To restrict by resource, use
   `Condition` with `aws:ResourceTag/*` or `aws:ResourceAccount`.

## Allow list vs Deny list strategy — decision guide

### Decision matrix

| Factor | Deny-list | Allow-list |
|---|---|---|
| Default posture | Allow (block known bad) | Deny (permit known good) |
| `FullAWSAccess` at entity | Keep attached | Detach (AFTER Allow-list attached) |
| Drift risk | New services auto-allowed | New services auto-denied |
| Onboarding friction | Low — services just work | High — each new service needs Allow |
| Audit overhead | Periodic review of new AWS services | Change-window per service addition |
| Compliance posture | Best for established orgs | Best for regulated industries |
| Break-glass complexity | Condition exemption or break-glass OU | Allow-list must include break-glass actions |
| Lockout risk if misconfigured | Low (only the Deny actions break) | High (a missing Allow = lockout) |

### The FullAWSAccess detach sequencing rule

When switching an entity from Deny-list (default) to Allow-list:

```text
Step 1: Attach the Allow-list SCP to the target entity
  aws organizations attach-policy --policy-id p-ALLOWLIST --target-id <id>

Step 2: Verify the Allow-list covers break-glass actions
  aws organizations describe-policy --policy-id p-ALLOWLIST
  # Confirm it Allows every action needed for break-glass,
  # including iam:* for the break-glass role.

Step 3: ONLY THEN detach FullAWSAccess
  aws organizations detach-policy --policy-id p-FullAWSAccess --target-id <id>

Step 4: Verify the detach took effect
  aws organizations list-policies-for-target --target-id <id> \
    --filter SERVICE_CONTROL_POLICY \
    --query 'Policies[?Name==`FullAWSAccess`]'   # should be empty
```

**NEVER reverse steps 1 and 3.** Detaching `FullAWSAccess` without
a replacement Allow-list leaves the entity in deny-by-default
state — every API call fails, including the calls needed to
re-attach the Allow-list from inside that account. Recovery must
come from the management account.

### Worked Allow-list example (correct sequence)

```text
Entity: OU_Prod_Data (ou-prod-data-001)
Allow-list SCP (p-prod-data-allow):
  Allow: ec2:*, s3:*, rds:*, iam:*, logs:Describe*

Sequence:
  1. aws organizations attach-policy --policy-id p-prod-data-allow --target-id ou-prod-data-001
     → effective Allow at OU = FullAWSAccess ∩ prod-data-allow = prod-data-allow
       (FullAWSAccess still attached but intersection already reduces to prod-data-allow)
     → BUT: FullAWSAccess is still attached, so the effective Allow is
       FullAWSAccess ∩ prod-data-allow, which equals prod-data-allow.
       WAIT — intersection of two Allows = intersection of two Allow sets.
       FullAWSAccess = Allow *, prod-data-allow = Allow specific set.
       Intersection = specific set. So the Allow-list is ALREADY effective.

  ⚠ Correction: removing FullAWSAccess is REQUIRED for the Allow-list to be
    effective because AWS Organizations treats the absence of any SCP at an
    entity as "Allow *" — and the presence of FullAWSAccess at the parent
    means the parent does NOT narrow the intersection. To NARROW at the
    child, the child entity must have FullAWSAccess DETACHED, otherwise the
    parent's FullAWSAccess is inherited implicitly.

  Actually: FullAWSAccess is a separate managed SCP. When attached at the
  parent, it means "Allow *" at the parent. The child inherits that. So:
    - If parent has FullAWSAccess: child's effective Allow = ⋂ of all
      Allows at parent + child = Allow * (parent) ⋂ child_Allow = child_Allow.
    - But the parent's FullAWSAccess ALSO applies to the child via inheritance.
      So the child's effective Allow = FullAWSAccess ⋂ child_Allow = child_Allow.

  Bottom line: detaching FullAWSAccess at the CHILD (where the Allow-list
  applies) is what makes the Allow-list take effect at that child. Detaching
  at the parent makes the parent itself enforce the Allow-list.

  2. aws organizations detach-policy --policy-id p-FullAWSAccess --target-id ou-prod-data-001
     → FullAWSAccess no longer attached at ou-prod-data-001.
     → Effective Allow at ou-prod-data-001 = prod-data-allow (only).
     → Accounts under ou-prod-data-001 now inherit ONLY prod-data-allow
       (plus whatever is attached at root and any intermediate OUs).
```

### Worked Allow-list example (LOCKOUT — wrong sequence)

```text
Entity: OU_Prod_Data (ou-prod-data-001)

WRONG sequence:
  1. aws organizations detach-policy --policy-id p-FullAWSAccess --target-id ou-prod-data-001
     → Effective Allow at ou-prod-data-001 = ∅ (empty intersection)
     → Every API call by every principal in every account under
       ou-prod-data-001 now FAILS with UnauthorizedOperation.
     → Break-glass roles cannot act. Recovery must come from
       a sibling entity or the management account.

  2. (Cannot run create-policy from inside the locked accounts.)
```

## Break-glass exception patterns

### Pattern A: break-glass OU

Carve out an OU whose SCP chain does NOT include the restrictive
Deny. Place break-glass accounts in that OU. The Deny is attached
at sibling OUs, never at the break-glass OU or its ancestors.

```text
Root [no restrictive Denies]
 ├─ OU_Prod    [Deny SCP attached — affects OU_Prod and children]
 │   ├─ OU_Prod_Apps
 │   └─ OU_Prod_Data
 └─ OU_BreakGlass  [NO restrictive SCP — Deny NOT inherited]
     └─ 111122223311 (break-glass account)
```

**Verification:**

```bash
aws organizations list-parents --child-id 111122223311
# Parent: OU_BreakGlass

aws organizations list-policies-for-target --target-id <OU_BreakGlass_id> \
  --filter SERVICE_CONTROL_POLICY --query 'Policies[*].Name' --output table
# Should NOT list the restrictive Deny SCP
```

### Pattern B: Condition-based exemption

Use `StringNotEquals` on `aws:PrincipalAccount` or
`aws:PrincipalARN` inside the Deny statement. These keys are
immutable and not attacker-controllable.

```json
{
  "Sid": "DenyIamDeleteRole",
  "Effect": "Deny",
  "Action": ["iam:DeleteRole", "iam:DetachRolePolicy"],
  "Resource": "*",
  "Condition": {
    "StringNotEquals": {
      "aws:PrincipalAccount": ["111122223311"]
    }
  }
}
```

**Multi-account break-glass list:**

```json
"Condition": {
  "StringNotEquals": {
    "aws:PrincipalAccount": ["111122223311", "444455556666"]
  }
}
```

### Forbidden keys (attacker-controllable)

NEVER use these condition keys for break-glass exemptions — they
are attacker-controllable via HTTP headers or request parameters:

- `aws:UserAgent` — set via HTTP `User-Agent` header
- `aws:Referer` — set via HTTP `Referer` header
- `aws:sourceVpce` — only safe for VPC endpoint controls, not for
  SCP-level break-glass
- Any key sourced from the request body

### Verifying the break-glass path AFTER attach

```bash
# From the break-glass account, attempt the Deny-listed action
aws iam delete-role --role-name TestBreakGlassExemption
# Expected: success (the exemption Condition matched)
# If it fails with UnauthorizedOperation, the Condition did NOT match
# and the break-glass path is broken.
```

Always run this verification BEFORE a real incident requires the
break-glass path.

## SCP evaluation order (full picture)

```text
At the time of an API call from a member-account principal:

  1. AWS gathers every SCP attached along the hierarchy to the account.
       root → OU_1 → ... → OU_N → account
       For each level: include every SCP attached at that level.

  2. EXPLICIT DENY check
       If ANY SCP along the chain has an explicit "Deny" for the
       action+resource+condition combination, the call is DENIED.
       No further evaluation matters.

  3. INTERSECTION ALLOW check
       The action must be in the Allow set of EVERY SCP along
       the chain (intersection). If ANY SCP omits it, the call
       is DENIED at the SCP filter.

  4. (Only if the call passes the SCP filter)
     IAM evaluation
       - Identity-based policies (Allow/Deny)
       - Resource-based policies (Allow for cross-account)
       - Permission boundaries (Allow/Deny)
       - Session policies (if assume-role was used)

  5. Final GRANT
       The call succeeds only if every layer ALLOWS and no layer DENIES.
```

### Common evaluation pitfalls

1. **An explicit Deny at root cannot be overridden lower.**
   There is no mechanism to "un-Deny" at a child OU. The only
   fix is to detach the Deny from root (or add a Condition
   exemption at root).

2. **The management account bypasses steps 1-3.** SCPs do not
   apply to the management (payer) account. A root Deny SCP
   does not block break-glass executed from the management
   account.

3. **Resource-based policies CANNOT override an SCP Deny.** A
   resource-based `Allow` from a cross-account S3 bucket policy
   is filtered by SCPs first. If the SCP denies, the call fails
   regardless of the resource policy.

4. **IAM `simulate-custom-policy` simulates IAM, NOT SCPs.**
   Use it as a pre-attach hint only. The source of truth is
   post-attach CloudTrail observation.

## Terraform examples

### Allow-list strategy at an OU (with FullAWSAccess detach)

```hcl
resource "aws_organizations_policy" "allowlist" {
  name = "prod-data-allowlist"
  type = "SERVICE_CONTROL_POLICY"
  description = "Allow-list for OU_Prod_Data"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowApprovedServices"
      Effect = "Allow"
      Action = ["ec2:*", "s3:*", "rds:*", "iam:*", "logs:Describe*"]
      Resource = "*"
    }]
  })
}

resource "aws_organizations_policy_attachment" "allowlist_to_ou" {
  policy_id = aws_organizations_policy.allowlist.id
  target_id = "ou-prod-data-001"
}

# CRITICAL: detach FullAWSAccess AFTER the Allow-list is attached
# Use depends_on to enforce ordering in Terraform
resource "aws_organizations_policy_attachment" "detach_fullawsaccess" {
  policy_id = "p-FullAWSAccess"   # AWS-managed, fixed ID
  target_id = "ou-prod-data-001"

  # Terraform does not have a "detach" resource. Use a null_resource
  # with local-exec, or manage FullAWSAccess attachment outside Terraform.
  # The attach/detach dance is the canonical sharp edge.

  depends_on = [aws_organizations_policy_attachment.allowlist_to_ou]
}
```

### Deny-list strategy at root with break-glass Condition

```hcl
resource "aws_organizations_policy" "root_guardrails" {
  name = "root-guardrails"
  type = "SERVICE_CONTROL_POLICY"
  description = "Root guardrails: block LeaveOrganization, CloudTrail tampering"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyLeaveOrg"
        Effect = "Deny"
        Action = "organizations:LeaveOrganization"
        Resource = "*"
        Condition = {
          StringNotEquals = {
            "aws:PrincipalAccount" = ["111122223311"]   # break-glass account
          }
        }
      },
      {
        Sid    = "DenyDisableCloudTrail"
        Effect = "Deny"
        Action = ["cloudtrail:DeleteTrail", "cloudtrail:StopLogging", "cloudtrail:PutEventSelectors"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_organizations_policy_attachment" "root_guardrails_to_root" {
  policy_id = aws_organizations_policy.root_guardrails.id
  target_id = "r-xxxx"
}
```
