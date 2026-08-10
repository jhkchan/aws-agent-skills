# Baseline (no-skill) response: delegated-admin-setup

This file captures what a generic assistant produces WITHOUT the
multi-account-governance-automator skill loaded.

---

To set up delegated administration, you need to designate an audit
account. Use the `enable-organization-admin-account` command for
GuardDuty and Security Hub, specifying the audit account ID.

For Config, create a configuration aggregator in the audit account. You
can add each member account as an aggregation source.

For CloudTrail, create an organization trail that delivers logs to an
S3 bucket in the log-archive account. Make sure the bucket policy
allows CloudTrail to write logs.

For IAM Identity Center, set up permission sets and assign them to
groups and accounts. You can configure federation with your corporate
IdP if needed.

Make sure each member account has Config and Security Hub enabled so
they send data to the aggregator.
