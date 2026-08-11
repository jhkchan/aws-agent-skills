---
name: managed-blockchain-deployer
description: >-
  Provisions AWS Managed Blockchain with production defaults: Hyperledger
  Fabric network creation (edition Starter vs Standard, framework version,
  voting policy), member creation (admin certificate, CA), peer node
  creation (instance type, Availability Zone, CloudWatch log config), CA
  enrollment, channel creation, chaincode lifecycle (install/instantiate
  1.4, approve/commit 2.x). Covers the separate Managed Blockchain
  Ethereum nodes (public mainnet/testnet) and the serverless Managed
  Blockchain Query API for on-chain reads (Ethereum, Bitcoin balances,
  transactions, contracts). Emits a READY_TO_DEPLOY checklist. Use when
  creating a Fabric network, adding consortium members, deploying peer
  nodes, installing chaincode, provisioning Ethereum nodes, or querying
  blockchain data. Triggers: create Managed Blockchain network,
  Hyperledger Fabric AWS, blockchain member, peer node, chaincode,
  certificate authority, Managed Blockchain Query, Ethereum node AWS.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with
  managedblockchain, managedblockchain-query, ec2, logs, and iam
  access. Works with Terraform aws_managedblockchain_* resources and
  CloudFormation AWS::ManagedBlockchain::* templates.
keywords:
  - aws
  - managed blockchain
  - cloudops
  - deploy
  - provisioning
  - hyperledger fabric
  - blockchain network
  - consortium
  - peer node
  - chaincode
  - certificate authority
  - ethereum
  - blockchain query
  - token balances
  - bitcoin
  - distributed ledger
tags:
  - aws
  - managed-blockchain
  - cloudops
  - deploy
  - analytics
  - provisioning
  - hyperledger-fabric
  - blockchain
  - ethereum
  - chaincode
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - managed-blockchain
    - cloudops
    - deploy
    - analytics
    - provisioning
    - hyperledger-fabric
    - blockchain
    - ethereum
    - chaincode
  dependencies:
    - aws-orchestrator
  keywords:
    - create managed blockchain network
    - hyperledger fabric aws
    - blockchain member creation
    - peer node provisioning
    - chaincode deployment
    - managed blockchain query
    - ethereum node aws
  when_to_use: >-
    Invoke when the user wants to create an AWS Managed Blockchain
    network (Hyperledger Fabric or Ethereum), add consortium members,
    deploy peer nodes, configure a certificate authority, install
    chaincode, create channels, provision Ethereum nodes, or query
    public blockchain data via the Managed Blockchain Query API. Do
    NOT invoke for Amazon QLDB, AWS KMS blockchain signing, or for
    auditing existing blockchain posture (use an auditor skill).
---

# Managed Blockchain Deployer

An AWS CloudOps agent skill that provisions AWS Managed Blockchain
resources with correct defaults. The skill walks the operator through
the three product lines (Fabric, Ethereum nodes, Query API), captures
edition, framework, member, and node decisions, and emits a
READY_TO_DEPLOY checklist with verification commands.

## Activation keywords

create Managed Blockchain network, Hyperledger Fabric AWS, blockchain
member creation, peer node provisioning, chaincode deployment, AWS
blockchain certificate authority, Managed Blockchain Query, Ethereum
node AWS, blockchain consortium, token balance query.

## STRICT output contract

When this skill is invoked with a Managed-Blockchain-provisioning
request (network creation, member addition, peer node, Ethereum node,
Query API access, or a partial configuration), the agent MUST respond
with the READY_TO_DEPLOY checklist defined in the "Output format"
section using the literal all-caps labels `MANAGED_BLOCKCHAIN:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT
preface the checklist with prose, headings, or disclaimers — emit the
block as the first lines of the response. This contract is what
assertion-based evals and downstream provisioning pipelines rely on;
deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Fabric vs Ethereum vs Query (product line decision) | Boundary call |
| Step 2 — Fabric network creation (edition, framework, voting policy) | New Fabric network |
| Step 3 — Member creation (admin certificate, CA, network config) | Consortium member |
| Step 4 — Peer node creation (instance type, AZ, log config) | Fabric node |
| Step 5 — Certificate authority enrollment | Admin cert lifecycle |
| Step 6 — Channel creation | Fabric channel |
| Step 7 — Chaincode lifecycle (1.4 vs 2.x) | Smart contracts |
| Step 8 — Managed Blockchain Ethereum nodes | Public Ethereum |
| Step 9 — Managed Blockchain Query API | Serverless on-chain reads |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/*.md | Fabric CLI sequence + Ethereum/Query detail |

## Mindset

**One-line takeaway:** AWS Managed Blockchain is three distinct
products behind one service name: (1) Hyperledger Fabric for private
consortium networks, (2) Ethereum nodes for public mainnet/testnet
participation, and (3) the Query API for serverless on-chain data
reads. They share a service namespace but almost nothing else —
mixing their concepts is the single most common provisioning error.

Three misconceptions dominate Managed Blockchain misdesign at
provisioning time:

- **"Starter edition is fine for production."** AWS announced Starter
  edition retirement: new Starter networks can no longer be created.
  Standard is the only supported path. A baseline happily provisions
  Starter.

- **"I need an Ethereum node to query on-chain data."** The Query API
  is a serverless HTTP API for token balances, transactions, and
  contract reads across Ethereum mainnet/testnet and Bitcoin. No node,
  no sync time, no instance cost. A baseline skips to node
  provisioning.

- **"Fabric channels and chaincode are AWS API operations."** They are
  not. AWS provisions the infrastructure (network, member, peer node,
  CA); channels and chaincode are Fabric-layer operations invoked via
  the Fabric SDK or CLI against the peer endpoint. Conflating the two
  leads to `aws managedblockchain create-channel` which does not exist.

## Configuration dependency graph (novel heuristic)

Managed Blockchain resources form a strict dependency chain. A
baseline model treats them as independent; the chain below forces
correct ordering and catches the "why can't I create a node?" errors.

| Resource | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Fabric network | edition + framework + voting policy + first member spec | **edition CANNOT be changed** after creation; Starter cannot be created post-retirement | network ID for all subsequent Fabric ops |
| Member | network ID (founder or invited) | admin cert must be enrolled BEFORE channel/chaincode ops; removal requires network vote | member ID for node creation |
| Peer node | member ID + VPC subnets in the node's AZ | **instance type CANNOT be changed** — must delete and recreate; CREATE → AVAILABLE takes 10-20 min | transaction endorsement, channel participation |
| Certificate authority | created automatically with the member | CA endpoint + TLS cert returned asynchronously; enrollment uses Fabric CA client | admin cert for channel/chaincode ops |
| Channel | >= 1 peer node (AVAILABLE) + admin cert | created via Fabric SDK/CLI, NOT the AWS API; AWS has no `create-channel` operation | private transaction lanes |
| Chaincode | peer node + channel + admin cert | Fabric 1.4 = install + instantiate; Fabric 2.x = approve + commit; mismatch breaks install | smart contract execution |
| Ethereum node | VPC subnets + framework ETHEREUM | syncs to mainnet/testnet; full sync takes hours/days | JSON-RPC endpoint (HTTP + WebSocket) |
| Query API call | IAM policy (AmazonManagedBlockchainQueryReadOnly) | **no node required** — fully serverless; rate-limited per account | token balances, tx history, contract reads |

**The immutable rows are what a baseline model misses.** Fabric
edition, peer-node instance type, and framework version are set at
creation and CANNOT be changed without destroying and recreating.

**Cross-dependency gotchas:**
- Member is not usable until its CA is AVAILABLE (poll `get-member`).
- Peer node VPC subnets must be in the same AZ as the node.
- Fabric 2.x lifecycle (approve/commit) is incompatible with 1.4
  (install/instantiate).
- Ethereum nodes and Fabric networks are completely separate.

## Expert heuristic: Starter edition retirement

Starter edition was announced for retirement. A baseline model
provisions Starter for cost; this skill blocks it.

```text
Operator: "Create a Starter Fabric network — it's cheaper."
Skill response:
  [✗] Edition: STARTER is NO LONGER AVAILABLE for new networks. Use STANDARD.
```

Existing Starter networks continue to run but cannot be upgraded to
Standard — you must migrate (export ledger, create Standard network,
re-import). The skill prevents provisioning a dead-end edition.

## Expert heuristic: three product lines, one service

```text
Managed Blockchain
├── Hyperledger Fabric  (private consortium)
│   create-network → create-member → create-node → CA enrollment
├── Ethereum nodes      (public mainnet/testnet)
│   create-node (framework=ETHEREUM) → JSON-RPC endpoint
└── Query API           (serverless on-chain reads, NO node)
    managedblockchain-query: get-token-balance, list-token-balances,
    list-transactions, get-contract — per-request, no sync
```

When an operator says "query the blockchain," the skill asks: do they
need to RUN a node (Ethereum node), or READ data (Query API)? For
most read-only use cases, the Query API is cheaper and faster.

## Expert heuristic: channel/chaincode is NOT an AWS API

AWS provisions Fabric infrastructure (network, member, node, CA).
Channels and chaincode are Fabric-layer operations via the peer CLI.
`aws managedblockchain create-channel` does not exist. (Covered in
detail in Steps 6-7 below.)

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with Managed Blockchain access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | Select regions only; not all support all product lines | `aws configure get region` |
| VPC + subnets (peer/Ethereum nodes) | Nodes are VPC-provisioned; subnets must be in the node's AZ | `aws ec2 describe-subnets` |
| Framework decision (Fabric vs Ethereum) | Determines the entire provisioning path | Confirm use case |
| Edition decision (Fabric only) | Starter retired; Standard only option for new networks | Confirm Standard |
| Fabric CA client installed | Admin cert enrollment uses the Fabric CA client | `fabric-ca-client version` |
| Fabric peer CLI installed | Channel and chaincode ops use the peer CLI | `peer version` |
| Query API IAM policy | Read-only access to on-chain data | Attach `AmazonManagedBlockchainQueryReadOnly` |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Fabric vs Ethereum vs Query (product line decision)

```text
Is the use case a PRIVATE consortium blockchain (multiple known parties)?
├── YES → Hyperledger Fabric
│         create-network + create-member + create-node + CA + channel + chaincode
│         Use for: supply chain, B2B settlement, consortium identity
│
└── NO  → Is the use case PUBLIC chain participation (run a full/node)?
    ├── YES → Managed Blockchain Ethereum node
    │         create-node (framework=ETHEREUM)
    │         Use for: dApp backend, indexer, self-hosted RPC
    │
    └── NO  → Is the use case READ-ONLY on-chain data (balances, txs)?
        ├── YES → Managed Blockchain Query API (NO node needed)
        │         Use for: wallet dashboards, compliance, tx monitoring
        └── NO  → Re-scope: likely QLDB (centralized ledger) or non-AWS chain
```

| Feature | Fabric | Ethereum node | Query API |
|---|---|---|---|
| Chain type | Private consortium | Public Ethereum | Public (read-only) |
| Provisioning effort | High | Medium (node + sync) | None (serverless) |
| Cost model | Per-node hourly + storage | Per-node hourly + storage | Per-request |
| Write capability | Yes (endorse+order) | Yes (submit tx) | No (read-only) |
| Sync time | N/A (private genesis) | Hours to days | None |
| Latency to first query | 30-60 min | Hours (after sync) | Seconds |

## Step 2 — Fabric network creation (edition, framework, voting policy)

Fabric network creation is the founder operation: it creates the
network AND the first member in one API call.

```bash
aws managedblockchain create-network \
  --name "consortium-supply-chain" \
  --description "Supply chain tracking consortium" \
  --framework HYPERLEDGER_FABRIC \
  --framework-version "2.2" \
  --network-configuration '{"Edition": "STANDARD"}' \
  --voting-policy '{
    "ApprovalThresholdPolicy": {
      "ThresholdPercentage": 50,
      "ProposalDurationInHours": 24,
      "ThresholdComparator": "GREATER_THAN"
    }
  }' \
  --member-configuration '{
    "Name": "founder-member",
    "FrameworkConfiguration": {
      "Fabric": {"AdminUsername": "admin", "AdminPassword": "Admin12345!"}
    }
  }' \
  --region us-east-1
```

**Critical decisions (immutable after creation):**

| Decision | Options | Immutable? |
|---|---|---|
| Edition | STARTER (retired) / STANDARD | Yes |
| Framework version | 1.4 / 2.2 | Yes |
| Voting policy (threshold %, duration) | Configurable | Yes (network default) |
| Founder member name + admin credentials | Configurable | Name immutable; password resettable |

**Common mistake:** specifying `STARTER` edition. The API rejects new
Starter networks post-retirement. Use `STANDARD`.

**Framework version guidance:** `2.2` is recommended for new networks
(new lifecycle, decentralized governance). `1.4` is legacy, for
compatibility with existing chaincode not yet migrated to 2.x.

## Step 3 — Member creation (admin certificate, CA, network config)

After the network exists, additional members are added via invitation
(`create-proposal` + `vote-on-proposal` for consortium governance),
then the invited member creates their member.

**Founder submits a proposal to invite a new member:**

```bash
aws managedblockchain create-proposal \
  --network-id n-ABCDEFGHIJ1234567 \
  --member-id m-ABCDEFGHIJ1234567 \
  --actions '{"Invitations": [{"Principal": "123456789012"}]}' \
  --region us-east-1
```

**Other members vote:**

```bash
aws managedblockchain vote-on-proposal \
  --network-id n-ABCDEFGHIJ1234567 \
  --proposal-id p-XXXXXXXXXX \
  --member-id m-ABCDEFGHIJ1234567 \
  --vote YES --region us-east-1
```

**The invited member creates their member:**

```bash
aws managedblockchain create-member \
  --invitation-id inv-XXXXXXXXXX \
  --network-id n-ABCDEFGHIJ1234567 \
  --member-configuration '{
    "Name": "logistics-partner",
    "FrameworkConfiguration": {
      "Fabric": {"AdminUsername": "admin", "AdminPassword": "Partner12345!"}
    }
  }' \
  --region us-east-1
```

Each member gets a managed CA automatically. The CA endpoint and TLS
certificate are returned via `get-member` once the member is
AVAILABLE. The admin must enroll with the CA to obtain the admin
certificate required for all channel and chaincode operations.

## Step 4 — Peer node creation (instance type, AZ, log config)

Peer nodes are the Fabric execution endpoints. Each member creates
its own peer node(s).

```bash
NODE_ID=$(aws managedblockchain create-node \
  --network-id n-ABCDEFGHIJ1234567 \
  --member-id m-ABCDEFGHIJ1234567 \
  --node-configuration '{
    "InstanceType": "bc.m5.large",
    "AvailabilityZone": "us-east-1a",
    "LogPublishingConfiguration": {
      "Fabric": {
        "ChaincodeLogs": {"CloudwatchLogsEnabled": true},
        "StateRequests": {"CloudwatchLogsEnabled": true},
        "Transactions": {"CloudwatchLogsEnabled": true}
      }
    }
  }' \
  --region us-east-1 \
  --query NodeId --output text)
```

**Node instance types (Fabric):**

| Instance type | vCPU | Memory | Use case |
|---|---|---|---|
| `bc.t3.small` | 2 | 2 GB | Dev/test (Starter only — deprecated) |
| `bc.m5.large` | 2 | 8 GB | Small production |
| `bc.m5.xlarge` | 4 | 16 GB | Medium production |
| `bc.c5.large` | 2 | 4 GB | Compute-heavy chaincode |
| `bc.c5.2xlarge` | 8 | 16 GB | Large production |

**Log publishing:** `ChaincodeLogs` (chaincode execution), 
`StateRequests` (state DB reads/writes), `Transactions` (endorsement
and validation). All publish to CloudWatch Logs. Enable all three for
production; disable `StateRequests` for high-throughput networks.

**Common mistake:** specifying an AZ without confirming the member's
VPC has a subnet in that AZ. The node creation fails silently or
hangs in CREATING state. Verify `aws ec2 describe-subnets` first.

**Immutable note:** the instance type CANNOT be changed after
creation. To resize, delete the node and create a new one (the
ledger state is preserved on the ordering service, but the peer must
re-sync).

## Step 5 — Certificate authority enrollment

The admin certificate is enrolled via the Fabric CA client (not the
AWS API). This must happen AFTER the member and CA are AVAILABLE.

**Retrieve CA endpoint:**

```bash
aws managedblockchain get-member \
  --network-id n-ABCDEFGHIJ1234567 \
  --member-id m-ABCDEFGHIJ1234567 \
  --region us-east-1 \
  --query 'Member.FrameworkAttributes.Fabric.CaEndpoint' --output text
# Output: ca.m-xxxxxxxxxxxxx.n-xxxxxxxxxxxx.managedblockchain.us-east-1.amazonaws.com:30002
```

**Download the CA TLS certificate:**

```bash
aws s3 cp \
  s3://us-east-1.managedblockchain/etc/managed-blockchain-tls-chain.pem \
  ./managed-blockchain-tls-chain.pem
```

**Enroll the admin identity:**

```bash
fabric-ca-client enroll \
  -u https://admin:Admin12345!@ca.m-xxxxxxxxxxxxx.n-xxxxxxxxxxxx.managedblockchain.us-east-1.amazonaws.com:30002 \
  --tls.certfiles ./managed-blockchain-tls-chain.pem \
  -M ./admin-msp
```

This produces the admin MSP directory containing the enrollment
certificate (`cert.pem`), private key (`keystore/`), CA root cert
(`cacert.pem`), and TLS CA cert (`TLScacert.pem`). This admin cert
authorizes channel creation, chaincode install, and instantiation.

## Step 6 — Channel creation

Channels are Fabric-layer private communication lanes between
subsets of consortium members. Channel creation uses the Fabric peer
CLI, not the AWS API.

```bash
export CORE_PEER_ADDRESS=nd-xxxxxxxxxxxxx.m-xxxxxxxxxxxxx.n-xxxxxxxxxxxx.managedblockchain.us-east-1.amazonaws.com:30003
export CORE_PEER_LOCALMSPID=m-ABCDEFGHIJ1234567MSP
export CORE_PEER_MSPCONFIGPATH=./admin-msp
export CORE_PEER_TLS_ROOTCERT_FILE=./managed-blockchain-tls-chain.pem

# Generate channel config transaction
configtxgen -profile OneOrgChannel -channelID supply-chain-channel -outputCreateChannelTx ./channel.tx

# Create the channel
peer channel create -c supply-chain-channel -f ./channel.tx \
  -o $ORDERER_ENDPOINT --tls --cafile ./managed-blockchain-tls-chain.pem

# Join the peer to the channel
peer channel join -b supply-chain-channel.block
```

**Common mistake:** attempting `aws managedblockchain create-channel`.
This API does not exist. Channels are a Fabric concept, not an AWS
resource. The AWS layer stops at the peer node.

## Step 7 — Chaincode lifecycle (install/instantiate vs approve/commit)

Chaincode deployment depends on the Fabric version.

**Fabric 1.4 (install + instantiate):**

```bash
peer chaincode install -n supply-chain-cc -v 1.0 -p github.com/example/supply-chain -l golang

peer chaincode instantiate -n supply-chain-cc -v 1.0 -C supply-chain-channel \
  -c '{"function":"init","Args":[]}' \
  -o $ORDERER_ENDPOINT --tls --cafile ./managed-blockchain-tls-chain.pem
```

**Fabric 2.x (approve + commit — new decentralized lifecycle):**

```bash
# Package
peer lifecycle chaincode package supply-chain-cc.tar.gz \
  --path github.com/example/supply-chain --lang golang --label supply-chain-cc_1.0

# Install
peer lifecycle chaincode install supply-chain-cc.tar.gz

# Approve for org
peer lifecycle chaincode approveformyorg -C supply-chain-channel \
  -n supply-chain-cc -v 1.0 --package-id $PACKAGE_ID --sequence 1 \
  --tls --cafile ./managed-blockchain-tls-chain.pem

# Commit (after enough orgs approve)
peer lifecycle chaincode commit -C supply-chain-channel \
  -n supply-chain-cc -v 1.0 --sequence 1 \
  --tls --cafile ./managed-blockchain-tls-chain.pem
```

**Version mismatch gotcha:** Fabric 1.4 lifecycle
(install/instantiate) is incompatible with Fabric 2.x lifecycle
(approve/commit). Using the wrong lifecycle against a channel on a
different framework version causes install failures. Match the
lifecycle to the network's framework version.

## Step 8 — Managed Blockchain Ethereum nodes

Ethereum nodes sync to the public Ethereum mainnet or testnet
(Sepolia/Holesky) and expose a JSON-RPC endpoint. No `create-network`
needed — the Ethereum network is the public chain; it already exists.

```bash
NODE_ID=$(aws managedblockchain create-node \
  --network-id n-ethereum-mainnet \
  --node-configuration '{
    "InstanceType": "bc.m5.large",
    "AvailabilityZone": "us-east-1a",
    "Framework": "ETHEREUM",
    "FrameworkConfiguration": {"Ethereum": {}},
    "LogPublishingConfiguration": {}
  }' \
  --region us-east-1 \
  --query NodeId --output text)
```

Ethereum networks use predefined IDs (`n-ethereum-mainnet`,
`n-ethereum-sepolia-testnet`, `n-ethereum-holesky-testnet`). You
only `create-node` to join.

**Retrieve the JSON-RPC endpoint:**

```bash
aws managedblockchain get-node \
  --network-id n-ethereum-mainnet \
  --node-id $NODE_ID \
  --region us-east-1 \
  --query 'Node.FrameworkAttributes.Ethereum.HttpEndpoint' --output text
```

Characteristics: syncs to mainnet/testnet (full sync takes hours to
days); HTTP and WebSocket JSON-RPC endpoints; no "member" concept
(Ethereum is account-based). Use cases: dApp backends, self-hosted
RPC, indexing, event monitoring.

**Common mistake:** calling `create-network` for Ethereum. The
Ethereum network is the public chain; it already exists. Use
predefined network IDs.

## Step 9 — Managed Blockchain Query API

The Query API is a fully serverless, read-only HTTP API for on-chain
data. No node provisioning, no sync time, no instance cost.

**Query a token balance:**

```bash
aws managedblockchain-query get-token-balance \
  --chain-id "ETH_MAINNET" \
  --owner-identifier '{"IdentifierType": "ADDRESS", "Identifier": "0x1234..."}' \
  --token-identifier '{"Network": "ETHEREUM", "ContractAddress": "0xdac8..."}' \
  --region us-east-1
```

**List all token balances for a wallet:**

```bash
aws managedblockchain-query list-token-balances \
  --owner-identifier '{"IdentifierType": "ADDRESS", "Identifier": "0x1234..."}' \
  --chain-id "ETH_MAINNET" --region us-east-1
```

**Get a transaction:**

```bash
aws managedblockchain-query get-transaction \
  --chain-id "ETH_MAINNET" \
  --transaction-hash "0xabcd1234..." --region us-east-1
```

Characteristics: supports Ethereum mainnet/testnet and Bitcoin;
IAM-controlled (standard AWS auth, no node keys); per-request pricing
(no hourly cost); no VPC required. Use cases: wallet dashboards,
compliance/AML screening, transaction monitoring, portfolio tracking.

**When to use Query API vs an Ethereum node:**

| Need | Query API | Ethereum node |
|---|---|---|
| Read token balances | Yes (faster, cheaper) | Overkill |
| List transactions | Yes | Overkill |
| Submit a transaction | No (read-only) | Yes |
| Subscribe to real-time events | No (polling only) | Yes (WebSocket) |
| Run custom archive queries | Limited | Yes |

**Common mistake:** provisioning a full Ethereum node (and waiting
hours for sync) when the operator only needs to read token balances.
The Query API returns the same data in seconds at a fraction of the
cost.

## Step 10 — Recent features

**Recent AWS features (2023-2026):**

- **Managed Blockchain Query API (2023-2024):** Serverless HTTP API
  for token balances, transactions, and contract data across Ethereum
  and Bitcoin. No node required.
- **Starter edition retirement (2024-2025):** New Starter Fabric
  networks can no longer be created. Standard is the only path.
- **Fabric 2.2 support (2023-2024):** New chaincode lifecycle
  (approve/commit), decentralized governance, private data
  collections.
- **Ethereum Sepolia/Holesky testnet (2024-2025):** New testnet
  networks as Goerli deprecated.
- **Bitcoin Query API support (2024-2025):** Query API extended to
  Bitcoin mainnet/testnet.
- **Batch query operations (2024-2025):** `batch-get-token-balance`
  and `list-filtered-transaction-events` for bulk reads.
- **Query API event filtering (2025-2026):** Filter by contract
  address, token ID, and event type.

## NEVER do these things

1. **NEVER specify STARTER edition for new Fabric networks.**
   Starter edition is retired — new Starter networks cannot be
   created. Use STANDARD. A baseline model may suggest Starter for
   cost savings; the API will reject the request.

2. **NEVER call `aws managedblockchain create-channel`.** This API
   does not exist. Channels are Fabric-layer operations invoked via
   the peer CLI or Fabric SDK. AWS has no channel-management API.

3. **NEVER provision a full Ethereum node for read-only queries.**
   If the operator only needs token balances, transactions, or
   contract reads, use the Query API (serverless, per-request
   pricing, no sync time). An Ethereum node is for write operations
   or real-time event subscriptions.

4. **NEVER attempt channel/chaincode operations before the admin
   certificate is enrolled.** The admin cert (enrolled via the Fabric
   CA client) is required for all channel and chaincode operations.
   Poll `get-member` until the CA is AVAILABLE first.

5. **NEVER mix Fabric 1.4 and 2.x chaincode lifecycles.** Fabric 1.4
   uses install/instantiate; Fabric 2.x uses approve/commit. Mixing
   them against a channel on a different framework version causes
   install failures.

6. **NEVER call `create-network` for Ethereum.** The Ethereum network
   is the public chain — it already exists. Use predefined network
   IDs (`n-ethereum-mainnet`). You only `create-node`.

7. **NEVER assume a peer node's instance type can be changed.** It is
   immutable. To resize, delete and recreate (peer must re-sync).

8. **NEVER create a peer node without confirming VPC subnets in the
   target AZ.** No subnet = silent creation failure.

9. **NEVER assume the CA is available immediately after member
   creation.** CA endpoint and TLS cert are returned asynchronously.
   Poll `get-member` until AVAILABLE.

10. **NEVER forget to enable CloudWatch log publishing.** Chaincode,
    state, and transaction logs are critical for debugging. Enable all
    three at node creation (cannot be added later without recreating).

11. **NEVER conflate Managed Blockchain with Amazon QLDB.** QLDB is
    centralized (single-party). Managed Blockchain is decentralized
    (multi-party consensus). Different problems.

12. **NEVER assume Ethereum nodes or Query API are in all regions.**
    Verify region support before provisioning.

## Output format

```text
MANAGED_BLOCKCHAIN: <product-line> — <identifier> (<arn-or-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Product line: Fabric | Ethereum node | Query API
  [✓|✗] Network: <network-id> (edition: STANDARD, framework: 2.2) | n-ethereum-mainnet | N/A (Query)
  [✓|✗] Member: <member-id> (admin: <username>) | N/A (Ethereum/Query)
  [✓|✗] Peer node: <node-id> (instance: bc.m5.large, AZ: us-east-1a) | N/A
  [✓|✗] Certificate authority: enrolled (admin cert MSP at ./admin-msp) | N/A
  [✓|✗] Log publishing: ChaincodeLogs, StateRequests, Transactions → CloudWatch | N/A
  [✓|✗] Channel: <channel-name> (created via peer CLI, joined) | N/A
  [✓|✗] Chaincode: <name> v<version> (lifecycle: approve/commit for 2.x) | N/A
  [✓|✗] Ethereum node: <node-id> (JSON-RPC endpoint: <url>) | N/A
  [✓|✗] Query API: IAM policy AmazonManagedBlockchainQueryReadOnly attached | N/A
  [✓|✗] Region: <region>
  [✓|✗] VPC/subnets: verified in AZ <az> | N/A (Query)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws managedblockchain get-network --network-id <id> --region <region>
  aws managedblockchain get-member --network-id <id> --member-id <id> --region <region>
  aws managedblockchain get-node --network-id <id> --node-id <id> --region <region>
  aws managedblockchain-query list-token-balances --owner-identifier ... --chain-id ETH_MAINNET --region <region>  # if Query API
```

### Worked example — Fabric Standard network with founder member and peer node

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
  [✓] Channel: supply-chain-channel (created via peer CLI, joined)
  [✓] Chaincode: supply-chain-cc v1.0 (lifecycle: approve/commit for 2.x)
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

## Error handling

### `create-network` fails with edition error
Operator specified `STARTER`. Starter is retired for new networks.
Change to `STANDARD` and retry.

### Member/node creation hangs in `CREATING`
CA endpoint or node not yet available. Poll `get-member` / `get-node`
every 60 seconds until status is `AVAILABLE` (typically 10-20 min).

### `create-node` fails with VPC/subnet error
The specified AZ has no subnet in the member's VPC. Run
`aws ec2 describe-subnets` to find available AZs, then re-create.

### `fabric-ca-client enroll` fails with connection refused
CA endpoint not yet AVAILABLE. Poll `get-member`. Verify the TLS
certificate was downloaded from the correct S3 path. Verify the
admin password matches member creation.

### Chaincode install fails with lifecycle mismatch
Operator using Fabric 1.4 lifecycle on a 2.x network, or vice versa.
Match the lifecycle to the framework version.

### Ethereum node JSON-RPC returns empty responses
Node is still syncing (hours to days). Check `get-node` status. For
read-only queries during sync, use the Query API instead.

### Query API returns `AccessDeniedException`
IAM role lacks `AmazonManagedBlockchainQueryReadOnly`. Attach the
managed policy or add `managedblockchain-query:*` permissions.

## Domain

AWS CloudOps / AWS Managed Blockchain Provisioning & Distributed Ledger
Infrastructure (Hyperledger Fabric, Ethereum, Query API).

## AWS documentation

- **Managed Blockchain User Guide** — https://docs.aws.amazon.com/managed-blockchain/latest/hyperledger-fabric-dev/what-is-managed-blockchain.html
- **Create a network (Fabric)** — https://docs.aws.amazon.com/managed-blockchain/latest/APIReference/API_CreateNetwork.html
- **Create a member** — https://docs.aws.amazon.com/managed-blockchain/latest/APIReference/API_CreateMember.html
- **Create a node** — https://docs.aws.amazon.com/managed-blockchain/latest/APIReference/API_CreateNode.html
- **Managed Blockchain Query API** — https://docs.aws.amazon.com/managed-blockchain/latest/query-reference/mbq.html
- **Ethereum on Managed Blockchain** — https://docs.aws.amazon.com/managed-blockchain/latest/ethereum-dev/ethereum-deployment.html
- **Fabric CA enrollment** — https://docs.aws.amazon.com/managed-blockchain/latest/hyperledger-fabric-dev/hyperledger-fabric-get-started-create-member.html
- **Log publishing configuration** — https://docs.aws.amazon.com/managed-blockchain/latest/hyperledger-fabric-dev/hyperledger-fabric-logs.html
