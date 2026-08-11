# End-to-End Example: AWS RAM Resource Share Provisioning

A walkthrough showing how to use the `ram-resource-share-deployer` skill
from invocation through verification. Mirrors the structured-eval pattern
of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a RAM resource share to share two subnets from a
centralized networking account with two application accounts. The share
requires:

- Resource share name: shared-subnets-prod
- Resource type: ec2:Subnet (two subnets)
- Principals: account IDs 111111111111, 222222222222
- Same Organization, all features enabled (auto-accept)
- Default AWS managed permission for subnets
- Allow external principals: false
- Tags: Environment=production, Application=networking

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-ram-resource-share
```

Then paste the resource share requirements.

### Option B: Natural language

```
You: "Share subnets subnet-abc123 and subnet-def456 from account
      123456789012 with accounts 111111111111 and 222222222222 via
      RAM. Same Organization. Default permission. Internal only."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy ram resource share"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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

---

## Step 3 — Provisioning commands

The skill generates the CLI sequence (from
`references/deployment-cli-commands.md`):

```bash
# Step 1: Create the resource share with subnets and principals
cat > /tmp/resource-share.json <<'EOF'
{
  "name": "shared-subnets-prod",
  "allowExternalPrincipals": false,
  "principals": ["111111111111", "222222222222"],
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

aws ram create-resource-share --cli-input-json file:///tmp/resource-share.json --region us-east-1

# Step 2: Verify the default managed permission is associated
aws ram list-resource-share-permissions \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1
```

---

## Step 4 — Post-provisioning verification

```bash
# Verify the resource share
aws ram get-resource-shares \
  --resource-share-arns arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# List principals in the share
aws ram list-principals \
  --resource-owner SELF \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# List resources in the share
aws ram list-resources \
  --resource-owner SELF \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1

# List permission associations
aws ram list-resource-share-permissions \
  --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod \
  --region us-east-1
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Allow external principals | Left as default true or unknown | false for intra-Org | External sharing requires manual invitation acceptance and widens blast radius |
| Principal type | Only account IDs | Organization/OU ARNs for fleet-wide | OU/Org shares auto-apply to new accounts; account IDs do not |
| Permission association | Often forgotten | Verified and listed | Without a permission, principals see the resource but cannot interact |
| Resource share status | Assumes ACTIVE | Verified ACTIVE vs PENDING | External shares stay PENDING until accepted; internal auto-activates |
| RAM vs VPC peering | May create peering instead | RAM subnet sharing for centralized arch | VPC peering is point-to-point; RAM sharing lets consumers create resources in the subnet |
| Customer-managed permissions | Not considered | Offered when default is too broad | Custom permissions restrict specific actions on shared resources |

---

## Related artifacts

- **Skill definition:** `skills/ram-resource-share-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/ram-resource-share-deployer/references/deployment-cli-commands.md`
- **Permissions, resource types, vs peering guide:** `skills/ram-resource-share-deployer/references/permissions-and-resource-types.md`
- **Slash command:** `commands/aws/deploy-ram-resource-share.md`
- **Eval suite:** `skills/ram-resource-share-deployer/evals/evals.json`
- **Legacy test cases:** `skills/ram-resource-share-deployer/eval/test-cases.yaml`
