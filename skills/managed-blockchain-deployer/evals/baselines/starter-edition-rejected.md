# Baseline (no-skill) — starter-edition-rejected

> This is the response a model produces **without** the skill
> definition. It provisions Starter edition without flagging the
> retirement, misses the Standard requirement, and lacks the
> PREREQUISITES_MISSING verdict format. Generated for with-skill-
> vs-baseline comparison.

---

Here's how to create your Starter Fabric network for a POC:

```bash
aws managedblockchain create-network \
  --name poc-net \
  --framework HYPERLEDGER_FABRIC \
  --framework-version 1.4 \
  --network-configuration '{"Edition": "STARTER"}' \
  --member-configuration '{"Name": "poc-member"}' \
  --region us-east-1
```

Then create a peer node:
```bash
aws managedblockchain create-node \
  --network-id n-xxx \
  --member-id m-xxx \
  --node-configuration '{"InstanceType": "bc.t3.small", "AvailabilityZone": "us-east-1a"}'
```

Starter edition is cheaper and should be fine for a small POC.
