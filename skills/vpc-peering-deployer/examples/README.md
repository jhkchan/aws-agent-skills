# End-to-End Example: VPC Peering Deployment

A walkthrough showing how to use the `vpc-peering-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a same-account, same-region VPC peering
connection between an application VPC and a data VPC with DNS
resolution and security group cross-references. The peering needs:

- Requester VPC: vpc-aaa11122 (10.0.0.0/16)
- Accepter VPC: vpc-bbb22233 (10.1.0.0/16)
- Same account: 123456789012
- Same region: us-east-1
- DNS resolution: enabled (both sides)
- Security group: sg-app references sg-data (cross-VPC, port 443)
- Route tables: rtb-app111 (requester), rtb-data222 (accepter)

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-vpc-peering
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a VPC peering connection between vpc-aaa11122 and
      vpc-bbb22233 in us-east-1. Same account 123456789012.
      Enable DNS resolution. Route tables rtb-app111 and
      rtb-data222."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a vpc peering connection"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
VPC_PEERING: vpc-aaa11122 ↔ vpc-bbb22233 (pcx-111222333)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Requester VPC: vpc-aaa11122 (10.0.0.0/16)
  [✓] Accepter VPC: vpc-bbb22233 (10.1.0.0/16)
  [✓] CIDR overlap check: PASS (10.0.0.0/16 and 10.1.0.0/16 do not overlap)
  [✓] Account topology: Same-account (123456789012)
  [✓] Region topology: Same-region (us-east-1)
  [✓] Peering connection: pcx-111222333 — ACTIVE
  [✓] Route table (requester): rtb-app111 → 10.1.0.0/16 via pcx-111222333
  [✓] Route table (accepter): rtb-data222 → 10.0.0.0/16 via pcx-111222333
  [✓] DNS resolution: AllowDnsResolutionFromPeeredVpc=true (both sides)
  [✓] Security group: cross-VPC reference (sg-app → sg-data via peering)
  [✓] IPv6 routing: IPv4 only
  [✓] Tags: Environment=production, Topology=app-to-data
VERIFICATION_COMMANDS:
  aws ec2 describe-vpc-peering-connections --vpc-peering-connection-ids pcx-111222333 --region us-east-1
  aws ec2 describe-route-tables --route-table-ids rtb-app111 --region us-east-1
  aws ec2 describe-route-tables --route-table-ids rtb-data222 --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the peering connection (requester)
PCX_ID=$(aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-aaa11122 --peer-vpc-id vpc-bbb22233 \
  --region us-east-1 \
  --query 'VpcPeeringConnection.VpcPeeringConnectionId' --output text)

# Step 2: Accept the peering (same account — immediate)
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id "$PCX_ID" --region us-east-1

# Step 3: Add requester route (VPC-A → VPC-B)
aws ec2 create-route \
  --route-table-id rtb-app111 --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id "$PCX_ID" --region us-east-1

# Step 4: Add accepter route (VPC-B → VPC-A) — CRITICAL
aws ec2 create-route \
  --route-table-id rtb-data222 --destination-cidr-block 10.0.0.0/16 \
  --vpc-peering-connection-id "$PCX_ID" --region us-east-1

# Step 5: Enable DNS resolution (both sides)
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id "$PCX_ID" \
  --requester-peering-connection-options AllowDnsResolutionFromPeeredVpc=true \
  --region us-east-1

aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id "$PCX_ID" \
  --accepter-peering-connection-options AllowDnsResolutionFromPeeredVpc=true \
  --region us-east-1

# Step 6: Security group cross-VPC reference (same acct + region)
aws ec2 authorize-security-group-ingress \
  --group-id sg-app \
  --ip-permissions \
    "IpProtocol=tcp,FromPort=443,ToPort=443,UserIdGroupPairs=[{GroupId=sg-data,VpcPeeringConnectionId=$PCX_ID}]" \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Peering connection status — should be active
aws ec2 describe-vpc-peering-connections \
  --vpc-peering-connection-ids pcx-111222333 \
  --query 'VpcPeeringConnections[0].Status' --region us-east-1

# Requester route table — verify route to 10.1.0.0/16
aws ec2 describe-route-tables \
  --route-table-ids rtb-app111 \
  --query 'RouteTables[0].Routes[?DestinationCidrBlock==`10.1.0.0/16`]' \
  --region us-east-1

# Accepter route table — verify route to 10.0.0.0/16
aws ec2 describe-route-tables \
  --route-table-ids rtb-data222 \
  --query 'RouteTables[0].Routes[?DestinationCidrBlock==`10.0.0.0/16`]' \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Route tables | Requester only | Both sides (requester + accepter) | Accepter route is #1 forgotten step; without it, no bidirectional traffic |
| DNS resolution | Not configured | AllowDnsResolutionFromPeeredVpc on both sides | Must be enabled on BOTH sides; one-sided does not work |
| SG cross-reference | Tries SG reference cross-account | CIDR-based for cross-account; SG ref for same-account | SG cross-references only work same account + same region |
| CIDR overlap | Not checked | Explicit overlap check before creating | Overlapping CIDRs silently break routing |
| Inter-region | Missing --peer-region | --peer-region specified | Inter-region peering requires peer-region parameter |

---

## Related artifacts

- **Skill definition:** `skills/vpc-peering-deployer/SKILL.md`
- **Routing and DNS guide:** `skills/vpc-peering-deployer/references/routing-and-dns.md`
- **Cross-account and security guide:** `skills/vpc-peering-deployer/references/cross-account-and-security.md`
- **Slash command:** `commands/aws/deploy-vpc-peering.md`
- **Eval suite:** `skills/vpc-peering-deployer/evals/evals.json`
- **Legacy test cases:** `skills/vpc-peering-deployer/eval/test-cases.yaml`
