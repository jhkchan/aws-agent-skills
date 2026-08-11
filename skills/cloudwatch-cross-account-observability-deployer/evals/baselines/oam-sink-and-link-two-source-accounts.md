# Baseline (no-skill) response: oam-sink-and-link-two-source-accounts

This file captures what a generic assistant produces WITHOUT the
cloudwatch-cross-account-observability-deployer skill loaded.

---

To share CloudWatch data across accounts, you can use the OAM
service. First create a sink in the monitoring account:

```
aws oam create-sink --name ProdObservabilitySink
```

Then in each source account, create a link:

```
aws oam create-link --sink-identifier <sink-arn> --label prod-app
```

You may need to set a sink policy. After a few minutes you should
see the metrics in the monitoring account's CloudWatch console.
