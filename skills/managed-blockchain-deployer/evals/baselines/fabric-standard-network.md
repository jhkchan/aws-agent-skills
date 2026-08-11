# Baseline (no-skill) — fabric-standard-network

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the Starter edition
> retirement, the STANDARD vs STARTER distinction, the CA enrollment
> prerequisite, the immutable instance type warning, the channel/
> chaincode layering (Fabric CLI vs AWS API), and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to create a blockchain network:

1. Create the network:
```bash
aws managedblockchain create-network \
  --name consortium-supply-chain \
  --framework HYPERLEDGER_FABRIC \
  --framework-version 1.4 \
  --network-configuration '{"Edition": "STARTER"}' \
  --member-configuration '{"Name": "founder-member"}'
```

2. Create a node:
```bash
aws managedblockchain create-node \
  --network-id n-xxx \
  --member-id m-xxx \
  --node-configuration '{"InstanceType": "bc.t3.small"}'
```

3. Set up channels and chaincode via the Fabric CLI.

That should work for your POC.
