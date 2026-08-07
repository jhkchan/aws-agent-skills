# Baseline (no-skill) response: scp-region-restriction

This file captures what a generic assistant produces WITHOUT the
iam-permission-troubleshooter skill loaded.

---

The error says an SCP is blocking the call. SCPs are organisation-level
policies that restrict what an account can do. There is one at your
production OU that limits actions to `us-east-1` and `us-west-2`, so
running in `ap-southeast-2` is being denied.

You should contact whoever manages your AWS Organization and ask them
to add `ap-southeast-2` to the SCP allowlist, or move your workload
back to `us-east-1`. SCPs cannot be overridden from the member account.

Alternatively, you could check whether the SCP is actually needed, or
deploy the workload to one of the allowed regions instead.
