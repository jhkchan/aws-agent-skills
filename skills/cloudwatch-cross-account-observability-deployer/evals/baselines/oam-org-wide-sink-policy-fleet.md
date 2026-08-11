# Baseline (no-skill) response: oam-org-wide-sink-policy-fleet

This file captures what a generic assistant produces WITHOUT the
cloudwatch-cross-account-observability-deployer skill loaded.

---

For a large fleet, you can create a sink and add each account to
the sink policy. Use a loop or script:

```
for account in 444455556666 777788889999 ...; do
  aws oam put-sink-policy --sink-identifier <arn> --policy ...
done
```

Then deploy links in each account with CloudFormation. You should
see data flow once the links are attached.
