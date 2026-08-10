# Baseline (no-skill) response: cross-account-route53-access-denied-blocked

This file captures what a generic assistant produces WITHOUT the
route53-failover-operator skill loaded.

---

The error indicates that the role in account B is not authorized to
perform `route53:ChangeResourceRecordSets` on the hosted zone in
account A. To fix this, you need to add a policy to the role in
account B that allows Route 53 access:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "route53:*",
    "Resource": "*"
  }]
}
```

Attach this policy to the `AppOpsRole` in account B and retry the
command.
