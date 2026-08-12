# Baseline (no-skill) response: cross-account-destination-policy-missing

---

Cross-account CloudWatch Logs delivery requires setup on both
accounts. The source account's IAM role has permission, but the
destination account also needs to allow the source to write. You need
to create a destination and attach a resource policy.

In the destination account:

```
aws logs put-destination \
  --destination-name CrossAccountDest \
  --target-arn arn:aws:logs:us-east-1:111111111111:log-group:/cross-account/* \
  --role-arn arn:aws:iam::111111111111:role/CWLDestinationRole

aws logs put-destination-policy \
  --destination-name CrossAccountDest \
  --access-policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::222222222222:root"},"Action":"logs:PutSubscriptionFilter"}]}'
```

Then set up a subscription filter in the source account pointing to
the destination.
