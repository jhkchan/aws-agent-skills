# Baseline (no-skill) response: no-ssl-default-param-group

This file captures what a generic assistant produces WITHOUT the
redshift-cluster-auditor skill loaded — the contrast that proves the skill
adds structure (the default-PG-is-read-only insight, the require_ssl location
in the parameter group, the pending-reboot caveat, and the migration
workflow).

---

This cluster looks pretty healthy — it is private, encrypted with a KMS
key, has audit logging on, and the security group is restricted to a
private CIDR.

One thing to flag: **require_ssl is false**. This means SQL clients can
connect without TLS, which is a compliance issue for most frameworks.
You should enable require_ssl.

Other observations:
- The cluster uses the default parameter group (default.redshift-1.0).
- Enhanced VPC routing is on.
- User activity logging is on.

To fix the SSL gap, you can modify the parameter group to set
require_ssl to true, then reboot the cluster.
