---
name: ram-resource-share-deployer
description: 'Provisions AWS RAM (Resource Access Manager) resource shares with correct production defaults: resource type selection (Subnet, Transit Gateway, License Manager, Dedicated Host, Capacity Reservation, Route53 Resolver rules, Image Builder components/images), principal association (account IDs, OU ARNs, organization ARN), permission association (AWS managed and customer-managed permissions), resource share vs VPC peering decision, allow-external-principals control, resource share status and promotion. Emits a READY_TO_DEPLOY checklist. Use when creating a RAM resource share, sharing subnets across accounts, sharing a Transit Gateway, sharing Route53 Resolver rules, sharing Dedicated Hosts or Capacity Reservations, sharing with an entire Organization or OU, or associating managed permissions. Triggers: create RAM resource share, share subnet, share transit gateway, RAM principals, RAM permission association, share Route53 Resolver rules, RAM organization share, customer-managed permissions.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ram, ec2, route53resolver, license-manager, imagebuilder, organizations, and sts access. Works with Terraform aws_ram_resource_share / aws_ram_principal_association / aws_ram_resource_association / aws_ram_permission resources, CloudFormation AWS::RAM::ResourceShare, and SAM templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, ram, resource-share, governance, cloudops, deploy, transit-gateway, subnet-sharing
  dependencies: aws-orchestrator
  keywords: aws, ram, resource-access-manager, resource-share, governance, cloudops, deploy, provisioning, organizations, transit-gateway, subnet-sharing, route53-resolver, license-manager, dedicated-host
  when_to_use: Invoke when the user wants to create a new RAM resource share, share subnets across accounts, share a Transit Gateway, share Route53 Resolver rules, share Dedicated Hosts or Capacity Reservations, share with an entire Organization or OU, associate managed or customer-managed permissions, or compare resource sharing vs VPC peering. Do NOT invoke for VPC peering connections (use vpc-network-deployer) or IAM cross-account roles (use iam-role-deployer).
---

# RAM Resource Share Deployer

An AWS CloudOps agent skill that provisions AWS RAM (Resource
Access Manager) resource shares with correct production
defaults. The skill walks the operator through a 9-step
provisioning procedure covering resource types, principal
associations, permission associations, and organization-level
sharing — explaining why each default matters and emitting a
READY_TO_DEPLOY checklist verifying every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the sharing topology matters | "Reasoning framework" |
| What to verify before provisioning | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Choosing resource type, principals | "Expert heuristic" |
| Sharing pattern matrix | "Pattern matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Permissions, resource types, vs peering | `references/permissions-and-resource-types.md` |

## Activation keywords

create RAM resource share, share subnet across accounts,
share Transit Gateway, RAM principal association,
RAM permission association, share Route53 Resolver rules,
RAM organization share, customer-managed permissions RAM,
RAM OU principal, License Manager sharing, Dedicated Host
sharing, Capacity Reservation sharing, Image Builder sharing,
RAM vs VPC peering, allow external principals RAM,
resource share promotion, AWS RAM resource type,
RAM resource association.

## STRICT output contract

When this skill is invoked with a RAM resource share
provisioning request (resource share name, resource type,
principals, or a partial existing configuration), the agent
MUST respond with the READY_TO_DEPLOY checklist defined in
"Output format" using the literal all-caps labels
`RESOURCE_SHARE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with
prose, headings, or disclaimers — emit the block as the first
lines of the response.

### Required output structure

1. `RESOURCE_SHARE: <resource-share-name>` — the RAM resource
   share being provisioned.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`
   — nothing else.
3. `CHECKLIST:` followed by indented lines, each prefixed with a
   status marker (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws ram ...`
   commands the operator can run.

### 6 FORBIDDEN output patterns (each silently breaks automation)

1. **FORBIDDEN — prose preamble before `RESOURCE_SHARE:`.** The
   first non-empty line MUST be `RESOURCE_SHARE:`. No "Here is
   your checklist…".
2. **FORBIDDEN — markdown variants of the labels.** Write
   `VERDICT:`, not `**VERDICT:**`, `### Verdict`, `Verdict =`, or
   `\`VERDICT\``. The labels are case-sensitive all-caps keywords.
3. **FORBIDDEN — swapping verdict tokens.** The verdict is exactly
   `READY_TO_DEPLOY` or `PREREQUISITES_MISSING` — not "ready",
   "missing", "BLOCKED", "OK", or "needs review".
4. **FORBIDDEN — omitting `VERIFICATION_COMMANDS:`.** Even when
   the verdict is `PREREQUISITES_MISSING`, include the commands
   the operator needs to verify the gaps.
5. **FORBIDDEN — extra sections after `VERIFICATION_COMMANDS:`.**
   The checklist block is the entire response. Put deeper
   explanation in `references/` files, not after the block.
6. **FORBIDDEN — status marker drift.** Use only `[✓]`, `[✗]`,
   `[OPTIONAL]`, `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`,
   `[WARN]`, or emoji markers.

### Perfect example (copy the shape exactly)

```text
RESOURCE_SHARE: shared-subnets-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Resource share name — shared-subnets-prod
  [✓]      Resource type — ec2:Subnet (subnet-abc123, subnet-def456)
  [✓]      Principals — 111111111111, 222222222222 (account IDs)
  [✓]      Permission association — AWSRAMDefaultPermissionSubnet (managed)
  [✓]      Allow external principals — false (internal accounts only)
  [✓]      Sharing visibility — INTERNAL (principals in same Organization)
  [✓]      Feature set — ALL (Organization all features enabled)
  [✓]      Resource share status — ACTIVE
  [✓]      Tags — Environment=production, Application=networking
  [OPTIONAL] Customer-managed permissions — none (using AWS managed default)
VERIFICATION_COMMANDS:
  aws ram get-resource-shares --resource-share-arns arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod
  aws ram list-principals --resource-owner SELF --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod
  aws ram list-resources --resource-owner SELF --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod
  aws ram list-permissions --resource-owner SELF
```

## Reasoning framework (why the sharing topology matters)

AWS RAM resource sharing has **resource type, principal, and
permission constraints** that make the procedure non-trivial:

1. **Resource type FIRST — determines available permissions.**
   Each resource type has a specific set of managed permissions.
   Subnets use `AWSRAMDefaultPermissionSubnet`. Transit Gateways
   use `AWSRAMDefaultPermissionTransitGateway`. The permission
   defines what the principal can do with the shared resource.

2. **Principal type — account IDs vs OU vs Organization.**
   RAM supports three principal types:
   - **Account IDs** (12-digit) — share with specific accounts.
     Each account must accept the invitation unless in the same
     Organization with all features.
   - **OU ARNs** (`arn:aws:organizations::master-account-id:ou/o-xxx/ou-yyy`)
     — share with all accounts in an OU. Auto-applies to accounts
     moved into the OU later.
   - **Organization ARN** (`arn:aws:organizations::master-account-id:organization/o-xxx`)
     — share with ALL accounts in the Organization. Auto-applies
     to new accounts.

3. **Resource share vs VPC peering — they serve different
   purposes.** VPC peering creates a point-to-point network
   connection between two VPCs. Resource sharing via RAM shares
   the resource itself (e.g., a subnet) so other accounts can
   create resources IN it. Subnet sharing via RAM is the
   foundation for AWS Network Firewall, centralized VPC
   architectures, and Transit Gateway attachments.

4. **Same-Organization auto-accept — the right pattern.** When
   the resource share is within an Organization with all features
   enabled, principals auto-accept the share — no invitation
   needed. External accounts (outside the Organization) receive
   an invitation that must be accepted via `AcceptResourceShare`.

5. **Permission association — managed vs customer-managed.**
   Each resource type has an AWS-managed default permission.
   Customer-managed permissions allow fine-grained control (e.g.,
   allow Create but not Delete on shared subnets). Customer-managed
   permissions must be created and associated per resource type.

6. **Allow external principals — security-sensitive flag.**
   By default, RAM shares within an Organization are internal.
   Sharing with accounts outside the Organization requires
   `allowExternalPrincipals: true`. This flag should be set
   deliberately and audited — it widens the blast radius.

7. **Resource share status — PENDING vs ACTIVE.** When a resource
   share is created with external principals, it starts as PENDING
   until the principal accepts. Within an Organization, it is
   immediately ACTIVE. The `PromoteResourceShareCreatedFromPolicy`
   API converts a resource share created from a resource-based
   policy to a standard RAM resource share.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Resource type and ARN** | The resource being shared must exist (subnet, transit gateway, resolver rule, etc.) and its ARN must be specified. | `aws ram list-resource-types` |
| **Principal IDs or ARNs** | Account IDs (12-digit), OU ARNs, or Organization ARN. Must be valid and accessible. | `aws organizations describe-organization`, `aws organizations list-organizational-units-for-parent` |
| **Organization all features (for org/OU sharing)** | Sharing with an Organization or OU ARN requires Organizations with all features enabled. | `aws organizations describe-organization --query 'Organization.FeatureSet'` |
| **Permission association** | Each resource type has a managed default permission. Customer-managed permissions must be created first. | `aws ram list-permissions --resource-owner SELF` |
| **Allow external principals** | Default is false. Set to true only when sharing with accounts outside the Organization. | Check sharing visibility |
| **IAM permissions** | Caller needs `ram:CreateResourceShare`, `ram:AssociateResourceShare`, `ram:AssociateResourceSharePermission`, plus resource-specific permissions. | `aws sts get-caller-identity` |

## Deployment procedure (apply in order)

### Step 1: Resource type selection

RAM supports sharing the following resource types:

| Resource type | Managed permission | Typical use case |
|---|---|---|
| `ec2:Subnet` | `AWSRAMDefaultPermissionSubnet` | Centralized VPC, shared networking, AWS Network Firewall |
| `ec2:TransitGateway` | `AWSRAMDefaultPermissionTransitGateway` | Hub-and-spoke network topology |
| `ec2:PrefixList` | `AWSRAMDefaultPermissionPrefixList` | Shared CIDR prefix lists |
| `route53resolver:ResolverRule` | `AWSRAMDefaultPermissionRoute53ResolverRule` | Centralized DNS resolution |
| `route53resolver:FirewallRuleGroup` | `AWSRAMDefaultPermissionRoute53ResolverFirewallRuleGroup` | DNS Firewall |
| `license-manager:LicenseConfiguration` | `AWSRAMDefaultPermissionLicenseConfiguration` | License management across accounts |
| `ec2:DedicatedHost` | `AWSRAMDefaultPermissionDedicatedHost` | Dedicated Host sharing for EC2 |
| `ec2:CapacityReservation` | `AWSRAMDefaultPermissionCapacityReservation` | Capacity Reservation sharing |
| `imagebuilder:Component` | `AWSRAMDefaultPermissionImageBuilderComponent` | EC2 Image Builder components |
| `imagebuilder:ImageRecipe` | `AWSRAMDefaultPermissionImageBuilderImageRecipe` | Image Builder recipes |
| `imagebuilder:Image` | `AWSRAMDefaultPermissionImageBuilderImage` | Built images |
| `glue:Catalog` | `AWSRAMDefaultPermissionGlueDatabase` | Lake Formation / Glue catalog |
| `codebuild:Project` | `AWSRAMDefaultPermissionCodeBuildProject` | CodeBuild project sharing |

### Step 2: Principal selection

| Principal type | Format | Auto-accept? | Applies to new accounts? |
|---|---|---|---|
| Account IDs | `111111111111`, `222222222222` | No (if external), Yes (if same Org) | No — must add new accounts manually |
| OU ARN | `arn:aws:organizations::master-account-id:ou/o-xxx/ou-yyy` | Yes (if same Org) | Yes — new accounts in OU auto-included |
| Organization ARN | `arn:aws:organizations::master-account-id:organization/o-xxx` | Yes (if same Org) | Yes — all current and future accounts |

**Decision rule:** use Organization or OU ARNs when sharing
within an Organization with all features. Use account IDs for
cross-Organization sharing or selective account sharing.

### Step 3: Create the resource share

```bash
cat > /tmp/resource-share.json <<'EOF'
{
  "name": "shared-subnets-prod",
  "allowExternalPrincipals": false,
  "principals": [
    "111111111111",
    "222222222222"
  ],
  "resources": [
    {
      "arn": "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abc123",
      "type": "ec2:Subnet"
    },
    {
      "arn": "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-def456",
      "type": "ec2:Subnet"
    }
  ],
  "tags": [
    { "Key": "Environment", "Value": "production" },
    { "Key": "Application", "Value": "networking" }
  ]
}
EOF

aws ram create-resource-share \
  --cli-input-json file:///tmp/resource-share.json \
  --region us-east-1
```

### Step 4: Share with Organization or OU

```bash
# Share with the entire Organization
aws ram create-resource-share \
  --name shared-tgw-org \
  --allow-external-principals false \
  --principals arn:aws:organizations::123456789012:organization/o-abc123def \
  --resources arn=arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-123,type=ec2:TransitGateway \
  --region us-east-1

# Share with a specific OU
aws ram create-resource-share \
  --name shared-resolver-rules-ou \
  --allow-external-principals false \
  --principals arn:aws:organizations::123456789012:ou/o-abc123def/ou-xyz456 \
  --resources arn=arn:aws:route53resolver:us-east-1:123456789012:resolver-rule/rslvr-rr-abc123,type=route53resolver:ResolverRule \
  --region us-east-1
```

### Step 5: Permission association

Each resource type has a default AWS-managed permission. For
fine-grained control, create and associate a customer-managed
permission:

```bash
# List available permissions for a resource type
aws ram list-permissions \
  --resource-type ec2:Subnet \
  --resource-owner SELF \
  --region us-east-1

# Create a customer-managed permission
cat > /tmp/permission.json <<'EOF'
{
  "name": "custom-subnet-permission",
  "resourceType": "ec2:Subnet",
  "policyTemplate": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:CreateNetworkInterface\",\"ec2:DescribeSubnets\"],\"Resource\":\"*\"}]}",
  "policyType": "MANAGED"
}
EOF

aws ram create-permission \
  --cli-input-json file:///tmp/permission.json \
  --region us-east-1

# Associate the permission with a resource share
PERMISSION_ARN=$(aws ram list-permissions \
  --resource-type ec2:Subnet \
  --resource-owner SELF \
  --query 'permissions[?name==`custom-subnet-permission`].arn' \
  --output text \
  --region us-east-1)

aws ram associate-resource-share-permission \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --permission-arn ${PERMISSION_ARN} \
  --region us-east-1
```

### Step 6: Associate additional resources

Step 6 CLI sequence (associate additional resources) moved verbatim to
[references/deployment-cli-commands.md](references/deployment-cli-commands.md).

### Step 7: Associate additional principals

Step 7 CLI sequence (associate additional principals) moved verbatim to
[references/deployment-cli-commands.md](references/deployment-cli-commands.md).

### Step 8: Accept resource share invitations (external only)

Step 8 invitation-acceptance flow and CLI moved verbatim to
[references/deployment-cli-commands.md](references/deployment-cli-commands.md).

### Step 9: Verification and post-deployment checks

Step 9 verification and post-deployment check commands moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

## Pattern matrix

| Pattern | Resource type | Principals | Permission | When to use |
|---|---|---|---|---|
| Shared subnets (centralized VPC) | `ec2:Subnet` | Account IDs or OU ARN | Default or custom | Centralized networking, Network Firewall |
| Transit Gateway sharing | `ec2:TransitGateway` | Organization ARN | Default | Hub-and-spoke across all accounts |
| DNS resolution sharing | `route53resolver:ResolverRule` | OU ARN | Default | Centralized DNS forwarding |
| DNS Firewall sharing | `route53resolver:FirewallRuleGroup` | Account IDs | Default | Shared DNS Firewall rules |
| Dedicated Host sharing | `ec2:DedicatedHost` | Account IDs | Default | Host allocation across accounts |
| Capacity Reservation | `ec2:CapacityReservation` | OU ARN | Default | Shared capacity pools |
| License Manager | `license-manager:LicenseConfiguration` | Organization ARN | Default | Org-wide license tracking |
| Image Builder | `imagebuilder:Component` | OU ARN | Default or custom | Shared build components |
| Prefix List sharing | `ec2:PrefixList` | Account IDs | Default | Shared CIDR lists |

## Resource share vs VPC peering

The RAM-share-vs-peering comparison table and decision rule moved verbatim to
[references/permissions-and-resource-types.md](references/permissions-and-resource-types.md).

## Recent AWS features (2024-2026)

Recent AWS feature notes (2024-2026) moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## NEVER (anti-patterns)

- NEVER create a resource share with `allowExternalPrincipals: true`
  when sharing within the same Organization. External principal
  sharing bypasses auto-accept and requires manual invitation
  acceptance. Use `false` for intra-Org shares.

- NEVER share a resource without first verifying the principal
  account IDs or ARNs are valid. An invalid principal silently
  creates a resource share association that never activates —
  the principal status stays PENDING indefinitely.

- NEVER assume external principals will auto-accept resource
  share invitations. Only principals within an Organization with
  all features auto-accept. External accounts must explicitly
  call `AcceptResourceShare`.

- NEVER create a VPC peering connection when the intent is to
  share subnets for centralized networking. VPC peering creates
  point-to-point routes; RAM subnet sharing lets other accounts
  create resources directly in the shared subnet. Use RAM for
  centralized architectures.

- NEVER associate a customer-managed permission without testing
  it first. A mis-scoped permission (e.g., denying
  `CreateNetworkInterface` on a shared subnet) silently breaks
  consumers that need to create ENIs (Lambda, RDS, NAT Gateway).

- NEVER omit the permission association for resource types that
  require it. Each resource type has a default managed permission
  — without it, the principal can see the shared resource but
  cannot interact with it.

- NEVER share a Transit Gateway without verifying that the
  consumer accounts have the correct RAM accept status. A TGW
  share that is not accepted results in failed TGW attachment
  creation on the consumer side.

- NEVER deviate from the checklist output format. Substituting
  `Verdict` / `**VERDICT**` / `### Verdict:` for the literal
  `VERDICT:` label silently breaks downstream deployment pipelines
  and assertion-based evals.

## Expert heuristic — choosing resource type and principals

The expert heuristic for choosing resource type and principals moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Pre-flight safety checks (run before any provisioning CLI)

Pre-flight safety check commands moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

## Output format — MANDATORY literal labels

When invoked with a RAM resource share provisioning request,
your ENTIRE response MUST be the checklist block below. The
labels are **case-sensitive all-caps keywords** — write them
EXACTLY as shown. Do NOT write a preamble. Start with
`RESOURCE_SHARE:` and stop after the `VERIFICATION_COMMANDS:`
block.

```text
RESOURCE_SHARE: <resource-share-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Resource share name — <name>
  [✓]      Resource type — <type> (<resource-arns>)
  [✓]      Principals — <account IDs | OU ARN | Organization ARN>
  [✓]      Permission association — <managed permission name | customer-managed>
  [✓]      Allow external principals — <true | false>
  [✓]      Sharing visibility — <INTERNAL | EXTERNAL>
  [✓]      Feature set — <ALL (Organization) | N/A>
  [✓]      Resource share status — <ACTIVE | PENDING>
  [✓]      Tags — <key=value pairs>
  [OPTIONAL] Customer-managed permissions — <name | none>
VERIFICATION_COMMANDS:
  aws ram get-resource-shares --resource-share-arns <resource-share-arn>
  aws ram list-principals --resource-owner SELF --resource-share-arn <resource-share-arn>
  aws ram list-resources --resource-owner SELF --resource-share-arn <resource-share-arn>
  aws ram list-resource-share-permissions --resource-share-arn <resource-share-arn>
```

**Status marker semantics:**
- `[✓]` — configuration is applied and verified.
- `[✗]` — configuration is NOT applied or is misconfigured. Cite
  the gap.
- `[OPTIONAL]` — recommended but not required for the sharing
  pattern.
- `[INPUT NEEDED]` — a prerequisite value is missing (resource
  ARN, principal IDs, permission ARN) and the operator must
  provide it before provisioning can proceed.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite
is missing (resource ARN, principal IDs or ARNs, Organization
not enabled with all features for org/OU sharing), the verdict
is `PREREQUISITES_MISSING` with each gap listed.

## Edge-case handling

The edge-case handling catalog moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — recent AWS features (2024-2026), expert heuristic for resource type and principal selection, edge-case handling catalog (moved from this file)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety checks and Step 9 post-deployment verification commands (moved from this file)
- [references/deployment-cli-commands.md](references/deployment-cli-commands.md) — full copy-pasteable CLI sequence for all 9 steps; extended with the Step 6-8 associate and invitation-acceptance commands
- [references/permissions-and-resource-types.md](references/permissions-and-resource-types.md) — shareable resource types, managed and customer-managed permissions, vs-VPC-peering decision matrix; extended with the comparison table and decision rule

## Domain

AWS CloudOps / AWS RAM Resource Access Manager Provisioning.

## AWS documentation

- **AWS RAM User Guide** — https://docs.aws.amazon.com/ram/latest/userguide/
- **RAM Resource Shares** — https://docs.aws.amazon.com/ram/latest/userguide/what-is.html
- **RAM Resource Types** — https://docs.aws.amazon.com/ram/latest/userguide/shareable.html
- **RAM Permissions** — https://docs.aws.amazon.com/ram/latest/userguide/permissions.html
- **RAM Customer-Managed Permissions** — https://docs.aws.amazon.com/ram/latest/userguide/working-with-customer-managed-permissions.html
- **RAM with Organizations** — https://docs.aws.amazon.com/ram/latest/userguide/working-with-organizations.html
- **RAM CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/ram/

## References

- `references/deployment-cli-commands.md` — full copy-pasteable CLI
  command sequence for all 9 provisioning steps, including resource
  share creation, principal association (account IDs, OU ARNs,
  Organization ARN), permission association (managed and
  customer-managed), resource association, invitation acceptance,
  and Terraform `aws_ram_resource_share` /
  `aws_ram_principal_association` /
  `aws_ram_resource_association` /
  `aws_ram_permission` resource equivalents.

- `references/permissions-and-resource-types.md` — deep reference
  on all shareable resource types and their managed permissions,
  customer-managed permission creation patterns, resource share vs
  VPC peering decision matrix, allow-external-principals security
  model, and multi-account sharing verification patterns.
