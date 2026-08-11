# Baseline (no-skill) response: custom-lambda-remediation

This file captures what a generic assistant produces WITHOUT the
config-rule-compliance-automator skill loaded.

---

For CIS 2.1 (default security group with no ingress rules), you'll need
a custom Lambda function since there's no managed rule for this. The
Lambda function should check if the default security group has any
ingress rules and mark it as NON_COMPLIANT if it does.

Write a Lambda function that uses the Config API to evaluate the SG and
calls put_evaluations with the compliance status.

For remediation, you could create a custom SSM Automation document that
revokes the ingress rules on the default SG. Set the remediation to
manual trigger since you want to review false positives first.

I think the general approach is:
1. Create the Lambda function
2. Register it as a Config rule
3. Create the SSM document
4. Wire remediation

The exact CLI commands would need to be looked up.
