# Baseline (no-skill) response: single-region-nlb-client-ip-preserve

This file captures what a generic assistant produces WITHOUT the
globalaccelerator-deployer skill loaded — the contrast that proves
the skill adds structure (PreserveClientIpEnabled decision matrix,
origin SG posture verification, CloudWatch service-linked role
check, deterministic VERDICT block).

---

Here's a plan to set up Global Accelerator in front of your NLB.

The accelerator will:

- Give you two static IPs
- Listen on TCP 443
- Route to your NLB
- Send logs to CloudWatch

Steps:

1. Create the accelerator.
2. Add a listener on port 443.
3. Add an endpoint group in us-east-1.
4. Add the NLB as an endpoint.
5. Configure flow logs to CloudWatch.

Commands:

```
aws globalaccelerator create-accelerator --name prod-ga-nlb-preserve-ip
aws globalaccelerator create-listener --protocol TCP --port-ranges 443
aws globalaccelerator add-endpoints --endpoint-configurations ...
```

Note that there's a setting for preserving client IP — you can
enable it if your application needs the real client IP. You may
need to update your security group. Let me know if you want help.
