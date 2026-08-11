# Baseline (no-skill) — query-token-balances

> This is the response a model produces **without** the skill
> definition. It suggests provisioning a full Ethereum node to
> read balances, missing the serverless Query API entirely, and
> lacks the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

To read token balances for an Ethereum address, you'll need to
run a node:

1. Create an Ethereum node:
```bash
aws managedblockchain create-node \
  --network-id n-ethereum-mainnet \
  --node-configuration '{"InstanceType": "bc.m5.large"}'
```

2. Wait for it to sync (may take several hours).

3. Use web3.js or ethers.js to call the ERC-20 balanceOf method
   via the node's JSON-RPC endpoint.

Alternatively, you could use a third-party API like Infura or
Alchemy for read-only queries.
