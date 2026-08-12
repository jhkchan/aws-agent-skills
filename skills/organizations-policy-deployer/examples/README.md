# End-to-End Example: Organizations Policy Deployment

A walkthrough showing how to use the `organizations-policy-deployer`
skill from invocation through verification. Mirrors the
structured-eval pattern of shipping a concrete worked example per
skill.

---

## Scenario

You are deploying a root-level Deny-list SCP that blocks
LeaveOrganization and CloudTrail tampering across the entire
org, with a break-glass OU carved out. The deployment needs:

- Organization: "All features" enabled, management account
  123456789012
- Policy name: `root-guardrails`
- Deny actions: `organizations:LeaveOrganization`,
  `cloudtrail:DeleteTrail`, `cloudtrail:StopLogging`,
  `cloudtrail:PutEventSelectors`
- Strategy: Deny-list (keep `FullAWSAccess`)
- Break-glass path: `OU_BreakGlass` (ou-bg-001) — the Deny must
  NOT be inherited there
- Attachment target: root `r-xxxx`
- Tag: `Governance=root-guardrails`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-organizations-policy
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a root SCP that blocks LeaveOrganization and
      CloudTrail tampering. Carve out a break-glass OU.
      Keep FullAWSAccess. Management account 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a root scp"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ORGANIZATIONS_POLICY: root-guardrails (p-aaa1bbb2) [SERVICE_CONTROL_POLICY] → root:r-xxxx
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Organization "All features" enabled
  [✓] Caller in management account: 123456789012
  [✓] Policy type enabled: SERVICE_CONTROL_POLICY (ENABLED)
  [✓] Policy JSON validated: implicitDeny on blocked actions
  [✓] Policy created: p-aaa1bbb2 — ENABLED
  [✓] Policy attached: p-aaa1bbb2 → root:r-xxxx
  [✓] Strategy: Deny-list (FullAWSAccess kept)
  [✓] FullAWSAccess at target: KEPT
  [✓] Break-glass path: OU_BreakGlass (ou-bg-001) — Deny NOT inherited
  [✓] CloudTrail org trail: org-management-trail — Logging
  [✓] Tags: Governance=root-guardrails
VERIFICATION_COMMANDS:
  aws organizations describe-policy --policy-id p-aaa1bbb2
  aws organizations list-policies-for-target --target-id r-xxxx --filter SERVICE_CONTROL_POLICY
  aws organizations list-parents --child-id 111122223311
  aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::111122223311:role/SCPTestRole --action-names organizations:LeaveOrganization
```

---

## Step 3 — Deployment commands

```bash
# Step 1: Author the SCP JSON (Deny-list with Condition-based break-glass)
POLICY_DOC=$(cat <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLeaveOrg",
      "Effect": "Deny",
      "Action": "organizations:LeaveOrganization",
      "Resource": "*",
      "Condition": { "StringNotEquals": { "aws:PrincipalAccount": ["111122223311"] } }
    },
    {
      "Sid": "DenyDisableCloudTrail",
      "Effect": "Deny",
      "Action": ["cloudtrail:DeleteTrail", "cloudtrail:StopLogging", "cloudtrail:PutEventSelectors"],
      "Resource": "*"
    }
  ]
}
EOF
)

# Step 2: Create the SCP
POLICY_ID=$(aws organizations create-policy \
  --content "$POLICY_DOC" \
  --description "Root guardrails: block LeaveOrganization and CloudTrail tampering" \
  --name "root-guardrails" --type SERVICE_CONTROL_POLICY \
  --tags Key=Governance,Value=root-guardrails \
  --query 'Policy.PolicySummary.Id' --output text)

# Step 3: Attach to root (FullAWSAccess stays — Deny-list strategy)
aws organizations attach-policy --policy-id "$POLICY_ID" --target-id r-xxxx

# Step 4: Verify OU_BreakGlass does NOT inherit the Deny
aws organizations list-policies-for-target --target-id ou-bg-001 \
  --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[*].Name' --output table
# Should NOT list root-guardrails (it's attached at root, but the OU's own
# chain plus the Condition exemption protects break-glass accounts).
```

---

## Step 4 — Post-deployment verification

```bash
# Confirm the SCP is attached at root
aws organizations list-policies-for-target --target-id r-xxxx \
  --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[?Name==`root-guardrails`].Id' --output text

# Confirm FullAWSAccess is STILL attached (Deny-list strategy)
aws organizations list-policies-for-target --target-id r-xxxx \
  --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[?Name==`FullAWSAccess`].Name' --output text
# Expected: FullAWSAccess

# Trace the OU chain at a child account to confirm intersection
aws organizations list-parents --child-id 111122223311

# Run a test call from a member account to confirm Deny takes effect
# (CloudTrail should show UnauthorizedOperation)
aws cloudtrail stop-logging --name test-trail
# Expected: An error occurred (AccessDeniedException) — SCP blocked

# Verify the break-glass account is NOT blocked
# (Run from the break-glass account)
aws organizations leave-organization
# Expected: success or different error (NOT SCP block)
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Strategy + FullAWSAccess | Detaches FullAWSAccess randomly | Keeps FullAWSAccess for Deny-list | Detaching without replacement Allow-list locks the account out of every API |
| Break-glass carve-out | No exemption | Condition-based exemption + break-glass OU | A root Deny hits every member account; break-glass must be carved out BEFORE attach |
| Inheritance behavior | Assumes "broadest wins" | Calls out intersection semantics | Child OUs can NARROW but not broaden; most-restrictive wins |
| Management account exemption | Expects SCP to constrain payer | Notes that management account is exempt from SCPs | SCPs never affect the payer — use IAM and break-glass procedures |
| Policy type enablement | Forgets TAG_POLICIES / BACKUP_POLICIES enable-policy-type | Forces enable-policy-type check | Non-SCP policy types require explicit enablement at root |
| simulate-custom-policy limit | Trusts IAM simulation as SCP truth | Notes that simulate is IAM-only, not Organizations | Post-attach CloudTrail observation is the source of truth |

---

## Related artifacts

- **Skill definition:** `skills/organizations-policy-deployer/SKILL.md`
- **Inheritance and strategy guide:** `skills/organizations-policy-deployer/references/scp-inheritance-and-strategy.md`
- **Policy types and delegation guide:** `skills/organizations-policy-deployer/references/policy-types-and-delegation.md`
- **Slash command:** `commands/aws/deploy-organizations-policy.md`
- **Eval suite:** `skills/organizations-policy-deployer/evals/evals.json`
- **Legacy test cases:** `skills/organizations-policy-deployer/eval/test-cases.yaml`
