# Baseline (no-skill) response: bulk-remediation-config-ssm

This file captures what a generic assistant produces WITHOUT the
tag-governance-automator skill loaded.

---

You can use the AWS Config required-tags managed rule to detect EC2
instances missing required tags. Then set up a remediation using SSM
Automation that adds the missing tags.

The Config rule would be the managed REQUIRED_TAGS rule. You
configure it with the tag keys you want to check.

For the remediation, you'd write a custom SSM Automation document
that calls ec2 create-tags on the instance. Wire it to the Config
rule via put-remediation-configurations.

Something like:

```
aws configservice put-remediation-configurations ...
```

The SSM document would take the instance ID as a parameter and add
the tags. You can set it to automatic so it fires whenever Config
detects a non-compliant instance.

Make sure the SSM role has permission to tag EC2 instances.
