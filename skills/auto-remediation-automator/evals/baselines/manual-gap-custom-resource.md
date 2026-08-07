# Baseline (no-skill) response: manual-gap-custom-resource

This file captures what a generic assistant produces WITHOUT the
auto-remediation-automator skill loaded.

---

To remediate open security groups automatically, you can write a
custom SSM Automation document that calls
`aws ec2 revoke-security-group-ingress`. Wire it to your Config rule
with `put-remediation-configurations` and set it to automatic.

The SSM document would look something like a script that calls the
API. You'd need to pass the security group ID as a parameter.

Once you create the SSM document and the remediation configuration,
the workflow should fire automatically.
