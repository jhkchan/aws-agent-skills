# RAM Resource Share Deployer — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Principals as Organization (2024-2025):** RAM now supports
  specifying the Organization ARN as a principal, automatically
  sharing with all current and future accounts. New accounts
  created in the Organization auto-receive the share.

- **Customer-managed permissions GA (2024-2025):** create custom
  permissions with fine-grained IAM policy templates per resource
  type. Associate with resource shares to control exactly what
  principals can do with shared resources (e.g., allow Create
  NetworkInterface but not Delete on shared subnets).

- **RAM Permission versioning (2025):** customer-managed
  permissions support versioning. Update a permission and all
  associated resource shares inherit the new version. Roll back
  by reverting to a previous version.

- **Resource share promotion (2024):** `PromoteResourceShareCreatedFromPolicy`
  converts a resource share implicitly created from a resource-based
  policy to a standard RAM resource share, enabling full management
  via RAM APIs.

- **Enhanced resource type support (2024-2025):** new shareable
  resource types including EC2 Image Builder pipelines, Route53
  Resolver Firewall rule groups, and Systems Manager documents.

- **RAM integration with AWS Organizations (2025):** deeper
  integration with Organizations trust policies — RAM validates
  principal ARNs against the Organization structure and
  auto-resolves OU membership changes.

## Expert heuristic — choosing resource type and principals (moved from SKILL.md)

**Resource type — determined by what you are sharing.** Each
resource type has its own managed permission. For subnets, the
default permission allows consumers to create network interfaces,
describe subnets, and create routes. For Transit Gateways, the
default allows consumers to create TGW attachments and routes.

**Principals — prefer Organization/OU ARNs for fleet-wide
sharing.** Use the Organization ARN to share with all accounts.
Use OU ARNs to share with specific organizational units. Use
account IDs for selective sharing or cross-Organization sharing.
Organization and OU ARN shares auto-apply to new accounts —
account ID shares do not.

**Allow external principals — false by default.** Set to true
only when sharing with accounts outside the Organization. Audit
this flag regularly — it is a security-sensitive setting.

**Permission association — start with AWS-managed defaults.**
The default managed permission covers most use cases. Create
customer-managed permissions only when you need to restrict
specific actions (e.g., prevent consumers from deleting shared
resources).

**Resource share status — verify ACTIVE.** After creating a
resource share, verify the status is ACTIVE. For Organization
shares, this is immediate. For external shares, the principal
must accept the invitation first.

## Edge-case handling (moved from SKILL.md)

- **Resource share status stays PENDING.** The principal has
  not accepted the invitation. For Organization shares, verify
  all features is enabled. For external accounts, the principal
  must call `AcceptResourceShare`.

- **Consumer cannot use shared subnet.** Verify the permission
  association is correct. The default permission for subnets
  allows `CreateNetworkInterface`. If using a customer-managed
  permission, verify the policy template includes the required
  actions.

- **OU ARN principal not accepted.** Verify the OU ARN is
  correct and the Organization has all features enabled. RAM
  validates OU ARNs against the Organization structure in real
  time.

- **Transit Gateway share fails on attachment creation.** The
  consumer account may not have accepted the TGW share, or the
  TGW may have reached its attachment limit. Verify the share
  status is ACTIVE on the consumer side.

- **Customer-managed permission not inheriting updates.**
  Customer-managed permissions support versioning. When you
  update a permission, verify all associated resource shares
  reference the latest version. Use `list-resource-share-permissions`
  to check the applied version.

