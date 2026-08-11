# Baseline (no-skill) response: byoip-cidr-not-provisioned

This file captures what a generic assistant produces WITHOUT the
globalaccelerator-deployer skill loaded — the contrast that proves
the skill catches the PENDING_PROVISIONING state blocker that the
baseline misses, emitting a deterministic PREREQUISITES_MISSING
verdict with the specific remediation (wait for PROVISIONED).

---

Here's a plan to set up Global Accelerator with your BYOIP CIDR.

The accelerator will:

- Use your BYOIP range 203.0.113.0/24
- Listen on TCP 443
- Route to your ALB

Steps:

1. Create the accelerator with the BYOIP CIDR.
2. Add a listener on port 443.
3. Add an endpoint group in us-east-1.
4. Add the ALB as an endpoint.

Commands:

```
aws globalaccelerator create-accelerator --name prod-ga-byoip \
  --byoip-cidrs 203.0.113.0/24
aws globalaccelerator create-listener --protocol TCP --port-ranges 443
aws globalaccelerator add-endpoints ...
```

You should be good to go once the BYOIP CIDR finishes provisioning
in Route 53. Let me know if you need help.
