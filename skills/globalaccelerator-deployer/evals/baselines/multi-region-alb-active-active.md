# Baseline (no-skill) response: multi-region-alb-active-active

This file captures what a generic assistant produces WITHOUT the
globalaccelerator-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated CHECKLIST,
specific DEPLOY_COMMANDS, expert knowledge of anycast IP semantics,
endpoint group homogeneity, traffic dial vs endpoint weight, and
client IP preservation per endpoint type).

---

Here's a plan to set up Global Accelerator in front of your two ALBs.

The accelerator will:

- Give you two static IPs
- Listen on TCP 443
- Route users to the closest region (us-east-1 or eu-west-1)
- Send logs to your S3 bucket

Steps:

1. Create the accelerator.
2. Add a listener on port 443.
3. Add endpoint groups for us-east-1 and eu-west-1.
4. Add your ALBs as endpoints.
5. Configure flow logs.

Commands:

```
aws globalaccelerator create-accelerator --name prod-ga-multi-region
aws globalaccelerator create-listener --protocol TCP --port-ranges 443
aws globalaccelerator create-endpoint-group ...
aws globalaccelerator add-endpoints ...
```

This should route traffic to the closest region automatically. Let
me know if you need help with any of the steps.
