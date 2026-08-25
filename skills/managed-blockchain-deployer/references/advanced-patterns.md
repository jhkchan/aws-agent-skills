# Managed Blockchain Deployer — advanced patterns (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Mindset — provisioning misconceptions (extended detail)

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

## Expert heuristics: Starter retirement, three product lines, channel/chaincode boundary

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

## Step 10 — Recent features (2023-2026)

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

