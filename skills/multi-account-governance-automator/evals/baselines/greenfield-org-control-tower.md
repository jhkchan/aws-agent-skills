# Baseline (no-skill) response: greenfield-org-control-tower

This file captures what a generic assistant produces WITHOUT the
multi-account-governance-automator skill loaded.

---

To set up a multi-account AWS organization, you'll want to use AWS
Organizations and Control Tower. First, enable Organizations in the
management account. Then create OUs for Security, Infrastructure, Prod,
NonProd, and Sandbox. Create accounts for audit and log-archive.

You can use the Control Tower console to set up the landing zone, which
will create the guardrails and Account Factory for you. For SCPs, you
can create policies that deny certain actions and attach them to the
root or OUs.

For delegated administration, you can enable GuardDuty and Security Hub
in the audit account. Set up a Config aggregator to collect compliance
data from all member accounts.

For SSO, use IAM Identity Center with permission sets. Create a few
permission sets like AdministratorAccess and ReadOnlyAccess and assign
them to groups.

Make sure to test everything in a sandbox account before deploying to
production.
