# Baseline (no-skill) response: mixed-endpoint-types-blocked

This file captures what a generic assistant produces WITHOUT the
globalaccelerator-deployer skill loaded — the contrast that proves
the skill catches the mixed-endpoint-type blocker that the baseline
misses (the API rejects ALB+NLB in the same endpoint group with
ValidationError).

---

Here's a plan to set up Global Accelerator in front of your ALB and
NLB.

The accelerator will:

- Give you two static IPs
- Listen on TCP 443
- Load-balance across both the ALB and the NLB

Steps:

1. Create the accelerator.
2. Add a listener on port 443.
3. Add an endpoint group in us-east-1.
4. Add both the ALB and the NLB as endpoints in the group.

Commands:

```
aws globalaccelerator create-accelerator --name prod-ga-mixed
aws globalaccelerator create-listener --protocol TCP --port-ranges 443
aws globalaccelerator add-endpoints --endpoint-configurations \
  '[{"EndpointId":"<alb-arn>","Weight":128},{"EndpointId":"<nlb-arn>","Weight":128}]'
```

This should let you load-balance across both. Let me know if you run
into any issues.
