# Ethereum Nodes & Query API — Managed Blockchain Deployer

Reference for the two non-Fabric Managed Blockchain product lines:
(1) Ethereum nodes for public mainnet/testnet participation, and
(2) the serverless Managed Blockchain Query API for on-chain data
reads. These are completely separate from Hyperledger Fabric.

## Part A: Managed Blockchain Ethereum Nodes

Ethereum nodes sync to the public Ethereum mainnet or testnet and
expose a JSON-RPC endpoint. No `create-network` needed — the network
is the public chain.

### Predefined Ethereum network IDs

| Network ID | Chain |
|---|---|
| `n-ethereum-mainnet` | Ethereum mainnet |
| `n-ethereum-sepolia-testnet` | Sepolia testnet |
| `n-ethereum-holesky-testnet` | Holesky testnet |

### Create an Ethereum node

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

echo "Node ID: $NODE_ID"
```

### Retrieve JSON-RPC endpoints

```bash
# HTTP endpoint
aws managedblockchain get-node \
  --network-id n-ethereum-mainnet \
  --node-id "$NODE_ID" \
  --region us-east-1 \
  --query 'Node.FrameworkAttributes.Ethereum.HttpEndpoint' --output text

# WebSocket endpoint
aws managedblockchain get-node \
  --network-id n-ethereum-mainnet \
  --node-id "$NODE_ID" \
  --region us-east-1 \
  --query 'Node.FrameworkAttributes.Ethereum.WebSocketEndpoint' --output text
```

### JSON-RPC usage (curl)

```bash
# Get latest block number
curl -X POST \
  -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  "$HTTP_ENDPOINT"

# Get account balance
curl -X POST \
  -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_getBalance","params":["0x1234...","latest"],"id":1}' \
  "$HTTP_ENDPOINT"
```

### Ethereum node characteristics

| Attribute | Detail |
|---|---|
| Sync type | Full sync (hours to days) |
| Endpoints | HTTP + WebSocket JSON-RPC |
| Authentication | None (endpoint URL is the credential) |
| Member concept | None (Ethereum is account-based) |
| Region availability | Select regions only |
| Pricing | Per-node hourly + storage |

### When to use an Ethereum node (vs Query API)

| Need | Use node | Use Query API |
|---|---|---|
| Submit transactions | Yes | No |
| Subscribe to real-time events (WebSocket) | Yes | No |
| Run debug/trace methods | Yes | No |
| Read token balances | Overkill | Yes |
| List transactions | Overkill | Yes |

---

## Part B: Managed Blockchain Query API

The Query API is a fully serverless, read-only HTTP API for on-chain
data. No node provisioning, no sync time, per-request pricing.

### Supported chains

| Chain ID | Chain |
|---|---|
| `ETH_MAINNET` | Ethereum mainnet |
| `ETH_SEPOLIA_TESTNET` | Ethereum Sepolia testnet |
| `ETH_HOLESKY_TESTNET` | Ethereum Holesky testnet |
| `BITCOIN_MAINNET` | Bitcoin mainnet |
| `BITCOIN_TESTNET` | Bitcoin testnet |

### IAM policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "managedblockchain-query:*"
      ],
      "Resource": "*"
    }
  ]
}
```

Or attach the AWS-managed policy:
`AmazonManagedBlockchainQueryReadOnly`

### Token balance queries

```bash
# Get a specific token balance
aws managedblockchain-query get-token-balance \
  --chain-id "ETH_MAINNET" \
  --owner-identifier '{
    "IdentifierType": "ADDRESS",
    "Identifier": "0x1234567890abcdef1234567890abcdef12345678"
  }' \
  --token-identifier '{
    "Network": "ETHEREUM",
    "ContractAddress": "0xdac817f7d243f8a1b1c0e4a2e5f6a7b8c9d0e1f2"
  }' \
  --region us-east-1

# List all token balances for a wallet
aws managedblockchain-query list-token-balances \
  --owner-identifier '{
    "IdentifierType": "ADDRESS",
    "Identifier": "0x1234567890abcdef1234567890abcdef12345678"
  }' \
  --chain-id "ETH_MAINNET" \
  --region us-east-1

# Batch get multiple token balances
aws managedblockchain-query batch-get-token-balance \
  --get-token-balance-inputs '[
    {
      "ownerIdentifier": {"identifierType": "ADDRESS", "identifier": "0x1111..."},
      "tokenIdentifier": {"network": "ETHEREUM", "contractAddress": "0xdac8..."}
    },
    {
      "ownerIdentifier": {"identifierType": "ADDRESS", "identifier": "0x2222..."},
      "tokenIdentifier": {"network": "ETHEREUM", "contractAddress": "0xa0b8..."}
    }
  ]' \
  --region us-east-1
```

### Transaction queries

```bash
# Get a specific transaction
aws managedblockchain-query get-transaction \
  --chain-id "ETH_MAINNET" \
  --transaction-hash "0xabcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab" \
  --region us-east-1

# List transactions for an address
aws managedblockchain-query list-transactions \
  --address "0x1234567890abcdef1234567890abcdef12345678" \
  --chain-id "ETH_MAINNET" \
  --region us-east-1

# List filtered transaction events
aws managedblockchain-query list-filtered-transaction-events \
  --chain-id "ETH_MAINNET" \
  --address "0x1234567890abcdef1234567890abcdef12345678" \
  --region us-east-1
```

### Contract queries

```bash
# Get contract metadata
aws managedblockchain-query get-contract \
  --chain-id "ETH_MAINNET" \
  --contract-address "0xdac817f7d243f8a1b1c0e4a2e5f6a7b8c9d0e1f2" \
  --region us-east-1

# List contracts for an address
aws managedblockchain-query list-contracts \
  --chain-id "ETH_MAINNET" \
  --contract-filter '{"DeployerAddress": "0x1234..."}' \
  --region us-east-1
```

### Query API characteristics

| Attribute | Detail |
|---|---|
| Provisioning | None (serverless) |
| Sync time | None |
| Pricing | Per-request |
| Auth | IAM (standard AWS auth, no node keys) |
| Write capability | No (read-only) |
| Real-time events | No (polling only) |
| VPC requirement | None |

### Verification

```bash
# Verify Query API access
aws managedblockchain-query list-token-balances \
  --owner-identifier '{"IdentifierType": "ADDRESS", "Identifier": "0x1234..."}' \
  --chain-id "ETH_MAINNET" \
  --region us-east-1 \
  --max-results 1

# Verify Ethereum node status
aws managedblockchain get-node \
  --network-id n-ethereum-mainnet \
  --node-id "$NODE_ID" \
  --region us-east-1 \
  --query 'Node.Status' --output text
# Expected: AVAILABLE (after sync completes)
```

---

## Step 8 — Ethereum node provisioning CLI (moved verbatim from SKILL.md)

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

## Step 9 — Query API CLI examples (moved verbatim from SKILL.md)

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

