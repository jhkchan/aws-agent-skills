# End-to-End Example: Managed Blockchain Deployment

A walkthrough showing how to use the `managed-blockchain-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Hyperledger Fabric network for a supply chain
consortium. The network needs:

- Product line: Hyperledger Fabric (private consortium)
- Edition: Standard (Starter is retired for new networks)
- Framework version: 2.2 (new chaincode lifecycle)
- Network name: consortium-supply-chain
- Founder member: founder-member (admin user: admin)
- Peer node: bc.m5.large in us-east-1a
- Log publishing: ChaincodeLogs, StateRequests, Transactions
- Region: us-east-1

Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-managed-blockchain
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Hyperledger Fabric Standard edition network on
      Managed Blockchain for a supply chain consortium. Fabric 2.2,
      founder member: founder-member, one bc.m5.large peer node in
      us-east-1a with CloudWatch logs. Region us-east-1."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create managed blockchain network"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
MANAGED_BLOCKCHAIN: Fabric — consortium-supply-chain (n-ABCDEFGHIJ1234567)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Product line: Fabric
  [✓] Network: n-ABCDEFGHIJ1234567 (edition: STANDARD, framework: 2.2)
  [✓] Member: m-ABCDEFGHIJ1234567 (admin: admin)
  [✓] Peer node: nd-XXXXXXXXXXXXX (instance: bc.m5.large, AZ: us-east-1a)
  [✓] Certificate authority: enrolled (admin cert MSP at ./admin-msp)
  [✓] Log publishing: ChaincodeLogs, StateRequests, Transactions → CloudWatch
  [✓] Channel: N/A (created post-network via peer CLI)
  [✓] Chaincode: N/A (installed post-channel)
  [✓] Ethereum node: N/A
  [✓] Query API: N/A
  [✓] Region: us-east-1
  [✓] VPC/subnets: verified in AZ us-east-1a
  [✓] Tags: Environment=production, Consortium=supply-chain
VERIFICATION_COMMANDS:
  aws managedblockchain get-network --network-id n-ABCDEFGHIJ1234567 --region us-east-1
  aws managedblockchain get-member --network-id n-ABCDEFGHIJ1234567 --member-id m-ABCDEFGHIJ1234567 --region us-east-1
  aws managedblockchain get-node --network-id n-ABCDEFGHIJ1234567 --node-id nd-XXXXXXXXXXXXX --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the Fabric Standard network + founder member
NETWORK_ID=$(aws managedblockchain create-network \
  --name "consortium-supply-chain" \
  --framework HYPERLEDGER_FABRIC \
  --framework-version "2.2" \
  --network-configuration '{"Edition": "STANDARD"}' \
  --voting-policy '{"ApprovalThresholdPolicy": {"ThresholdPercentage": 50, "ProposalDurationInHours": 24, "ThresholdComparator": "GREATER_THAN"}}' \
  --member-configuration '{"Name": "founder-member", "FrameworkConfiguration": {"Fabric": {"AdminUsername": "admin", "AdminPassword": "Admin12345!"}}}' \
  --region us-east-1 \
  --query NetworkId --output text)

# Step 2: Wait for member AVAILABLE, then get CA endpoint
aws managedblockchain get-member \
  --network-id "$NETWORK_ID" \
  --member-id "$MEMBER_ID" \
  --region us-east-1

# Step 3: Create peer node
NODE_ID=$(aws managedblockchain create-node \
  --network-id "$NETWORK_ID" \
  --member-id "$MEMBER_ID" \
  --node-configuration '{"InstanceType": "bc.m5.large", "AvailabilityZone": "us-east-1a", "LogPublishingConfiguration": {"Fabric": {"ChaincodeLogs": {"CloudwatchLogsEnabled": true}, "StateRequests": {"CloudwatchLogsEnabled": true}, "Transactions": {"CloudwatchLogsEnabled": true}}}}' \
  --region us-east-1 \
  --query NodeId --output text)

# Step 4: Download CA TLS cert and enroll admin
aws s3 cp s3://us-east-1.managedblockchain/etc/managed-blockchain-tls-chain.pem ./managed-blockchain-tls-chain.pem
fabric-ca-client enroll -u "https://admin:Admin12345!@$CA_ENDPOINT" --tls.certfiles ./managed-blockchain-tls-chain.pem -M ./admin-msp
```

---

## Step 4 — Post-deployment verification

```bash
# Network status
aws managedblockchain get-network \
  --network-id "$NETWORK_ID" \
  --region us-east-1

# Member status + CA endpoint
aws managedblockchain get-member \
  --network-id "$NETWORK_ID" \
  --member-id "$MEMBER_ID" \
  --region us-east-1

# Node status + endpoints
aws managedblockchain get-node \
  --network-id "$NETWORK_ID" \
  --node-id "$NODE_ID" \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Edition | STARTER (cheaper) | STANDARD | Starter is retired for new networks; API rejects it |
| Framework version | 1.4 (any) | 2.2 (recommended) | 2.x has new lifecycle, governance, data collections |
| Chaincode lifecycle | install/instantiate | approve/commit (2.x) | 2.x uses decentralized lifecycle; 1.4 lifecycle fails on 2.x |
| CA enrollment | Skipped | Required before channel/chaincode | Peer rejects admin ops without enrolled cert |
| Ethereum vs Fabric | Conflated | Separate product lines | Different APIs, concepts, and use cases |
| Query API | Provisions a node | Serverless API (no node) | Read-only queries don't need a node |
| Channel creation | `aws managedblockchain create-channel` | `peer channel create` (Fabric CLI) | AWS has no channel API; channels are Fabric-layer |

---

## Related artifacts

- **Skill definition:** `skills/managed-blockchain-deployer/SKILL.md`
- **Fabric provisioning commands:** `skills/managed-blockchain-deployer/references/fabric-provisioning-commands.md`
- **Ethereum + Query API guide:** `skills/managed-blockchain-deployer/references/ethereum-and-query-api.md`
- **Slash command:** `commands/aws/deploy-managed-blockchain.md`
- **Eval suite:** `skills/managed-blockchain-deployer/evals/evals.json`
- **Legacy test cases:** `skills/managed-blockchain-deployer/eval/test-cases.yaml`
