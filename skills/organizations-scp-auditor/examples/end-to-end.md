# End-to-end usage scenario: organizations-scp-auditor

A walkthrough showing the skill auditing an organization that has a
catastrophic CONFIG_GAP (FullAWSAccess detached from root with no
Allow replacement) combined with a PERMISSIVE_SCP finding (no
LeaveOrganization deny), demonstrating severity aggregation, the
mode-switch concept, and the remediation workflow.

## Input (user prompt)

> We just restructured our Organizations OU hierarchy and I'm seeing
> AccessDenied errors everywhere. Can you audit our SCPs?

```text
Organization structure for audit:

Root (r-prod-org-root):
  Attached SCPs:
    - (FullAWSAccess was DETACHED during restructuring)
    - DenyNonProdRegions:
      {"Version":"2012-10-17","Statement":[{"Effect":"Deny","NotAction":["iam:*","organizations:*","route53:*","cloudfront:*"],"Resource":"*","Condition":{"StringNotEquals":{"aws:RequestedRegion":["us-east-1"]}}}]}

OU "Production" (ou-prod-workloads):
  Parent: Root
  Attached SCPs:
    - (FullAWSAccess: NOT inherited — detached at root)
    - DenyNonProdRegions: inherited

Account 111122223333 "prod-app":
  Parent: OU "Production"
  Attached SCPs:
    - DenyNonProdRegions: inherited

Effective SCP evaluation for account 111122223333:
  - FullAWSAccess: NOT PRESENT (detached at root, no Allow replacement)
  - DenyNonProdRegions — present, inherited
  - organizations:LeaveOrganization: NOT denied (no Deny SCP for this action)
```

## Skill output

```text
TARGET: 111122223333 (prod-app)
VERDICT: CONFIG_GAP
REASON: FullAWSAccess is detached from the root with no Allow-list
replacement SCP in the effective chain — every action is implicitly
denied at the SCP layer, causing uniform AccessDenied across all
services (Step 1a). organizations:LeaveOrganization is also not denied.
FINDINGS:
  - [CONFIG_GAP] FullAWSAccess detached from root with no Allow SCP
    replacement (Step 1a) — every IAM Allow is filtered out; all
    workloads in all member accounts are blocked
  - [PERMISSIVE_SCP] organizations:LeaveOrganization not denied in
    effective hierarchy (Step 2a) — if access were restored, any account
    admin could leave the org and escape all SCPs
  - [OK] DenyNonProdRegions region restriction is syntactically valid
    and uses supported condition key aws:RequestedRegion
REMEDIATION:
  1. IMMEDIATE: Determine whether FullAWSAccess detachment was
     intentional (allow-list strategy) or accidental.
  2. If accidental, re-attach: aws organizations attach-policy
     --policy-id p-FULLAWSACCESS --target-id r-prod-org-root
  3. If intentional (allow-list mode), create an Allow SCP listing
     approved services and attach at root before proceeding.
  4. After restoring access, add a Deny SCP for
     organizations:LeaveOrganization at root level.
```

## Key decisions in this audit

1. **CONFIG_GAP takes priority over PERMISSIVE_SCP.** The
   FullAWSAccess detachment is classified first because it breaks the
   SCP model itself — no evaluation can be trusted until it is fixed.
   The LeaveOrganization finding is still enumerated but the verdict is
   CONFIG_GAP (higher severity).

2. **The region-restriction SCP is noted as OK** even though
   FullAWSAccess is detached. The region SCP is syntactically valid
   and uses a supported condition key — it would work correctly once
   the Allow gap is fixed. The skill does not conflate "broken by
   missing Allow" with "broken by bad Deny."

3. **The remediation does NOT auto-reattach FullAWSAccess.** The
   pre-flight safety check requires operator confirmation because the
   org may have intentionally moved to allow-list mode. Re-attaching
   FullAWSAccess would undo that strategy.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Audit specialist for Organizations Governance).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of roles
  operating within the SCP boundary.
