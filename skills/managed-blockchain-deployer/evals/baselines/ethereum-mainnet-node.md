# Baseline (no-skill) — ethereum-mainnet-node

> This is the response a model produces **without** the skill
> definition. It gives a rough command but misses the predefined
> network ID convention, the JSON-RPC endpoint retrieval, the
> distinction between Fabric and Ethereum product lines, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

To create an Ethereum node on Managed Blockchain:

1. Create the network first:
```bash
aws managedblockchain create-network --framework ETHEREUM
```

2. Then create a node:
```bash
aws managedblockchain create-node \
  --network-id n-xxx \
  --node-configuration '{"InstanceType": "bc.m5.large"}'
```

3. Use the endpoint URL for JSON-RPC calls once the node is ready.
