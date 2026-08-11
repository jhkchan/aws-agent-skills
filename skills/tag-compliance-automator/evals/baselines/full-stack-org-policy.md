# Baseline (no-skill) response: full-stack-org-policy

This file captures what a generic assistant produces WITHOUT the
tag-compliance-automator skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, four-layer stack,
enforced_for enforcement, propagation handler, cost allocation
activation, expert case-sensitivity knowledge).

---

To set up tag compliance across your organization, you should create a
tag policy in AWS Organizations and attach it to the root. Then deploy
Config rules to check for required tags, and a Lambda function to
auto-tag new resources.

You can use the AWS CLI to create the tag policy:

```
aws organizations create-policy --type TAG_POLICY --name tag-policy --content ...
```

For Config, deploy the required-tags managed rule and set the tag keys
you want to enforce. You can also add an EventBridge rule that triggers
a Lambda on RunInstances to stamp the Environment and Owner tags.

Make sure to activate your cost allocation tags in the Billing console
so they show up in Cost Explorer.

I don't have the exact JSON for the tag policy or the Lambda code
memorized — you'd need to look those up in the AWS documentation. The
tag policy should list your required keys and allowed values. The
Lambda should use the EC2 create-tags API to tag the instance.
