# Baseline (no-skill) response: cross-account-endpoint-shared

This file captures what a generic assistant produces WITHOUT the
globalaccelerator-deployer skill loaded — the contrast that proves
the skill adds structure (RAM share ACTIVE verification, cross-account
endpoint ARN validation, deterministic VERDICT block, deploy plan
with explicit RAM pre-check).

---

Here's a plan to set up a cross-account Global Accelerator.

The accelerator will:

- Live in your network account (111111111111)
- Use two static IPs
- Listen on TCP 443
- Route to the ALB in your workload account (222222222222)

Steps:

1. Make sure the RAM share is set up.
2. Create the accelerator in the network account.
3. Add a listener on port 443.
4. Add an endpoint group in us-east-1.
5. Add the workload account ALB as the endpoint.
6. Configure flow logs.

Commands:

```
aws globalaccelerator create-accelerator --name prod-ga-cross-account
aws globalaccelerator create-listener --protocol TCP --port-ranges 443
aws globalaccelerator add-endpoints --endpoint-configurations ...
```

Cross-account should work as long as the share is accepted. Let me
know if you need help with the RAM setup.
