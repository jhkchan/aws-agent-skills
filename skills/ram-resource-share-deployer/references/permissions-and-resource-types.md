# Permissions, Resource Types, and Sharing Patterns — RAM Resource Share Deployer

Deep reference on all shareable resource types, managed and
customer-managed permissions, resource share vs VPC peering decision,
allow-external-principals security model, and multi-account sharing
verification patterns.

## Shareable resource types

RAM supports sharing the following resource types, each with a
specific AWS-managed default permission:

### Networking

| Resource type | Default permission | What consumers can do |
|---|---|---|
| `ec2:Subnet` | `AWSRAMDefaultPermissionSubnet` | Create network interfaces (ENIs), describe subnets, create routes |
| `ec2:TransitGateway` | `AWSRAMDefaultPermissionTransitGateway` | Create TGW attachments, create routes, describe TGW |
| `ec2:PrefixList` | `AWSRAMDefaultPermissionPrefixList` | Reference shared prefix lists in route tables and security groups |
| `route53resolver:ResolverRule` | `AWSRAMDefaultPermissionRoute53ResolverRule` | Associate resolver rules with VPCs |
| `route53resolver:FirewallRuleGroup` | `AWSRAMDefaultPermissionRoute53ResolverFirewallRuleGroup` | Associate firewall rule groups with VPCs |

### Compute and licensing

| Resource type | Default permission | What consumers can do |
|---|---|---|
| `ec2:DedicatedHost` | `AWSRAMDefaultPermissionDedicatedHost` | Launch instances onto shared Dedicated Hosts |
| `ec2:CapacityReservation` | `AWSRAMDefaultPermissionCapacityReservation` | Launch instances using shared capacity reservations |
| `license-manager:LicenseConfiguration` | `AWSRAMDefaultPermissionLicenseConfiguration` | Track license usage against shared configurations |

### Image Builder and data

| Resource type | Default permission | What consumers can do |
|---|---|---|
| `imagebuilder:Component` | `AWSRAMDefaultPermissionImageBuilderComponent` | Use shared Image Builder components in pipelines |
| `imagebuilder:ImageRecipe` | `AWSRAMDefaultPermissionImageBuilderImageRecipe` | Use shared image recipes |
| `imagebuilder:Image` | `AWSRAMDefaultPermissionImageBuilderImage` | Use shared built images |
| `imagebuilder:DistributionConfiguration` | `AWSRAMDefaultPermissionImageBuilderDistributionConfiguration` | Use shared distribution configs |
| `glue:Catalog` | `AWSRAMDefaultPermissionGlueDatabase` | Access shared Glue/Lake Formation databases |

### Developer tools

| Resource type | Default permission | What consumers can do |
|---|---|---|
| `codebuild:Project` | `AWSRAMDefaultPermissionCodeBuildProject` | Run shared CodeBuild projects |

## Permission association

### AWS-managed permissions (default)

Each resource type has an AWS-managed default permission that is
automatically associated when the resource share is created. This
permission grants the standard set of actions needed to use the
shared resource.

```bash
# List available managed permissions for a resource type
aws ram list-permissions \
  --resource-type ec2:Subnet \
  --resource-owner SELF \
  --region us-east-1
```

### Customer-managed permissions (2024-2025)

Customer-managed permissions allow fine-grained control over what
principals can do with shared resources. Create a permission with
a policy template and associate it with a resource share.

```bash
# Create a customer-managed permission
cat > /tmp/permission.json <<'EOF'
{
  "name": "custom-subnet-restricted",
  "resourceType": "ec2:Subnet",
  "policyTemplate": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:CreateNetworkInterface\",\"ec2:DescribeSubnets\",\"ec2:DeleteNetworkInterface\"],\"Resource\":\"*\"}]}",
  "policyType": "MANAGED"
}
EOF

aws ram create-permission \
  --cli-input-json file:///tmp/permission.json \
  --region us-east-1
```

**Versioning:** customer-managed permissions support versioning.
When you update a permission, all associated resource shares
inherit the new version. Use `list-resource-share-permissions` to
check the applied version.

## Resource share vs VPC peering

### When to use RAM resource sharing

- **Centralized networking:** share subnets from a central
  networking account to application accounts. Consumers create
  ENIs, Lambda functions, RDS instances directly in the shared
  subnet.
- **Transit Gateway sharing:** share a TGW with all accounts so
  each can create attachments and route traffic through the
  central TGW.
- **DNS resolution:** share Route53 Resolver rules so all
  accounts resolve DNS through a central resolver.
- **Shared infrastructure:** share Dedicated Hosts, Capacity
  Reservations, or License Configurations across accounts.

### When to use VPC peering

- **Simple point-to-point connectivity:** two VPCs need to
  communicate directly.
- **Small number of VPCs:** peering connections scale as N^2
  (each pair needs its own connection). RAM subnet sharing scales
  linearly.

### Decision matrix

| Requirement | RAM resource share | VPC peering |
|---|---|---|
| Share a subnet for centralized networking | YES | NO (peering does not share subnets) |
| Connect two VPCs for bidirectional traffic | Possible (via shared subnet) | YES |
| Scale to many accounts | YES (one share, many principals) | NO (N^2 connections) |
| Transitive routing | YES (shared resources are transitive) | NO (peering is non-transitive) |
| Bandwidth aggregation | No limit (direct VPC resource) | Limited by peering aggregate |
| Cross-region | YES (share across regions) | YES (cross-region peering) |
| Data transfer cost | In-VPC traffic is free | Cross-region peering incurs data transfer |

## Allow-external-principals security model

The `allowExternalPrincipals` flag controls whether the resource
share can be shared with accounts outside the AWS Organization.

### Internal sharing (recommended default)

```bash
aws ram create-resource-share \
  --name shared-subnets-prod \
  --allow-external-principals false \
  ...
```

- Principals must be within the same Organization.
- Invitations auto-accept (no manual step).
- New accounts added to the Organization/OU auto-receive shares.
- No data leaves the Organization boundary.

### External sharing

```bash
aws ram create-resource-share \
  --name shared-subnets-partner \
  --allow-external-principals true \
  --principals 999999999999 \
  ...
```

- Principals can be outside the Organization (partner accounts,
  customer accounts).
- Invitations must be manually accepted via `AcceptResourceShare`.
- Wider blast radius — audit this flag regularly.
- Use for controlled cross-Organization partnerships.

## Multi-account sharing verification patterns

### Verify all shares for a resource

```bash
# List all resource shares
aws ram get-resource-shares --resource-owner SELF --region us-east-1

# List shares for a specific resource
aws ram list-resources --resource-owner SELF --region us-east-1
```

### Verify principal acceptance status

```bash
# List principals and their status
aws ram list-principals \
  --resource-owner SELF \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1
```

Status values: `ACTIVE` (accepted), `PENDING` (invitation sent,
not yet accepted), `ASSOCIATING`, `FAILED`.

### Cross-account resource verification

On a consumer account, verify the shared resources are visible:

```bash
# List resource shares received by this account
aws ram get-resource-shares --resource-owner OTHER-ACCOUNTS --region us-east-1

# List shared resources visible to this account
aws ram list-resources --resource-owner OTHER-ACCOUNTS --region us-east-1

# Describe a shared subnet (on the consumer account)
aws ec2 describe-subnets --subnet-ids subnet-abc123 --region us-east-1
```

### Audit: external principal sharing

```bash
# Find all resource shares with allowExternalPrincipals=true
aws ram get-resource-shares \
  --resource-owner SELF \
  --resource-share-status ACTIVE \
  --region us-east-1 \
  --query 'resourceShares[?allowExternalPrincipals==`true`]'
```

## Promoting resource shares

A resource share created implicitly from a resource-based policy
can be promoted to a standard RAM resource share:

```bash
aws ram promote-resource-share-created-from-policy \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/auto-created-share \
  --region us-east-1
```

This enables full management via RAM APIs (add/remove principals,
associate permissions, set tags).

---

## Resource share vs VPC peering (moved from SKILL.md)

| Aspect | RAM resource share (subnet) | VPC peering |
|---|---|---|
| **What is shared** | The subnet itself — other accounts create resources IN it | A network route between two VPCs |
| **Direction** | One-way (owner shares, consumers use) | Bi-directional (both VPCs route to each other) |
| **Transitivity** | Shared subnets are accessible by all principals | Non-transitive (A↔B, B↔C does not mean A↔C) |
| **Scalability** | One share per resource, many principals | One peering per pair (N^2 connections) |
| **Bandwidth** | No bandwidth limit (direct VPC resource) | Limited by peering connection aggregate |
| **Use case** | Centralized networking, shared services VPC | Simple point-to-point VPC connectivity |
| **Cost** | No data transfer cost for in-VPC traffic | Cross-region peering incurs data transfer |

**Rule:** use RAM subnet sharing for centralized architectures
(shared services VPC, centralized egress, Network Firewall).
Use VPC peering for simple point-to-point connectivity between
a small number of VPCs.

