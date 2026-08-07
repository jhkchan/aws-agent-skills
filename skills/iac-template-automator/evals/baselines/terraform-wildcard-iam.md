# Baseline (no-skill) response: terraform-wildcard-iam

This file captures what a generic assistant produces WITHOUT the
iac-template-automator skill loaded.

---

This Terraform configuration creates an IAM role with an attached policy.
The role is configured for general-purpose application access. The
policy grants broad permissions to allow the application to interact
with any AWS service it might need. This is a common pattern for
prototyping or for applications with dynamic permission requirements.
