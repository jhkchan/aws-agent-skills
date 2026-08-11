# Baseline (no-skill) — fabric-chaincode-2x

> This is the response a model produces **without** the skill
> definition. It gives generic chaincode commands but misses the
> Fabric 2.x lifecycle distinction (approve/commit vs
> install/instantiate), does not cite the network/member/node
> dependency chain, and lacks the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

To deploy chaincode on your Fabric network:

1. Install the chaincode:
```bash
peer chaincode install -n supply-chain-cc -v 1.0 -p github.com/example/supply-chain
```

2. Instantiate it:
```bash
peer chaincode instantiate -n supply-chain-cc -v 1.0 -C supply-chain-channel
```

3. Test with an invoke:
```bash
peer chaincode invoke -n supply-chain-cc -C supply-chain-channel -c '{"function":"init","Args":[]}'
```

That's the basic flow.
