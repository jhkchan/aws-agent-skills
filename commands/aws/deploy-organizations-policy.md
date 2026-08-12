---
description: Deploys AWS Organizations policy artifacts (SCPs, tag policies, backup policies, AI services opt-out policies) with production-grade defaults — Allow list vs Deny list strategy, FullAWSAccess management, inheritance as intersection, break-glass carve-out, policy simulation, and delegated administrator. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create scp"
  - "attach scp"
  - "deploy scp"
  - "service control policy"
  - "organizations policy"
  - "scp inheritance"
  - "allow list scp"
  - "deny list scp"
  - "fullawsaccess"
  - "tag policy"
  - "backup policy"
  - "ai services opt-out"
  - "break-glass scp"
  - "organizations delegated administrator"
  - "scp simulation"
routes_to: organizations-policy-deployer
---

# /aws:deploy-organizations-policy

Activate the `organizations-policy-deployer` skill and deploy an
AWS Organizations policy artifact with production-grade defaults.

## What it does

The skill walks the deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. SCP fundamentals (permission boundary, not IAM)
2. SCP creation (JSON policy via create-policy)
3. Attachment to root / OU / account
4. SCP inheritance (intersection of parent and child)
5. Allow list vs Deny list strategy
6. FullAWSAccess managed policy (detach sequencing)
7. SCP evaluation (explicit Deny wins)
8. Tag policy integration (enforced_for)
9. Backup policy integration
10. AI services opt-out policy
11. Multi-OU deployment & policy simulation
12. SCP exceptions (break-glass accounts)
13. CloudTrail for SCP-denied actions
14. Organizations delegated administrator
15. Recent features (effective-SCP viz, expanded delegations)

## When to use

- You need to create or attach an SCP.
- You are switching from Deny-list to Allow-list strategy (or
  vice versa).
- You are configuring FullAWSAccess detach.
- You are deploying a root-level Deny and need a break-glass
  carve-out.
- You need a tag policy, backup policy, or AI services opt-out
  policy.
- You are setting up a delegated administrator.
- You need to audit SCP-denied API calls in CloudTrail.

## When NOT to use

- **IAM permission boundaries** within a single account — use
  IAM skills. SCPs are not IAM.
- **Resource Access Manager (RAM) sharing** — different
  sharing model.
- **AWS Control Tower guardrails** — Control Tower wraps SCPs
  with its own lifecycle; use the control-tower skill.
- **Account factory / new account provisioning** — use the
  account-factory skill.

## How to invoke

### Slash command

```
/aws:deploy-organizations-policy
```

Then provide: policy name, policy type (SCP / TAG_POLICIES /
BACKUP_POLICY / AISERVICES_OPT_OUT_POLICY), JSON content,
target entity (root/OU/account ID), strategy (Allow-list or
Deny-list), FullAWSAccess decision (keep or detach), break-glass
path (if applicable), tags.

### Natural language

Any of these routes to the same skill:

- "create an SCP blocking LeaveOrganization at root"
- "switch OU_Prod_Data to Allow-list strategy"
- "deploy a tag policy with EnforcedFor ec2:instance"
- "set up a break-glass carve-out for the root Deny SCP"
- "delegate Access Analyzer administration to account 111122223311"

### CLI routing

```bash
node cli/bin/cli.js route "create a root scp"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline, in the **Governance** family. The orchestrator routes
to it when the user wants to create or attach Organizations
policies. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-organizations-policy

     Create a root SCP that blocks LeaveOrganization and
     CloudTrail tampering. Keep FullAWSAccess. Carve out
     OU_BreakGlass. Management account 123456789012.

Skill:
  ORGANIZATIONS_POLICY: root-guardrails (p-aaa1bbb2)
                         [SERVICE_CONTROL_POLICY] → root:r-xxxx
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Strategy: Deny-list (FullAWSAccess kept)
    [✓] Policy attached: p-aaa1bbb2 → root:r-xxxx
    [✓] Break-glass path: OU_BreakGlass — Deny NOT inherited
  VERIFICATION_COMMANDS:
    aws organizations describe-policy --policy-id p-aaa1bbb2
    aws organizations list-policies-for-target --target-id r-xxxx --filter SERVICE_CONTROL_POLICY
```

## References

- Skill definition: `skills/organizations-policy-deployer/SKILL.md`
- Inheritance and strategy guide: `skills/organizations-policy-deployer/references/scp-inheritance-and-strategy.md`
- Policy types and delegation guide: `skills/organizations-policy-deployer/references/policy-types-and-delegation.md`
- Eval suite: `skills/organizations-policy-deployer/evals/evals.json`
