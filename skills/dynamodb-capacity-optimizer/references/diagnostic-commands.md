# Diagnostic Commands (load on demand) — DynamoDB Capacity Optimizer

Pre-remediation safety checks and apply-time CLI moved verbatim from SKILL.md. Loaded on demand.

---

## CLI for right-sizing (with auto-scaling) (moved from SKILL.md)

**CLI for right-sizing (with auto-scaling):**
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb --resource-id table/my-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity <new_min> --max-capacity <new_max>

aws application-autoscaling put-scaling-policy \
  --policy-name my-table-read-scaling \
  --service-namespace dynamodb --resource-id table/my-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":60}'
```

---

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Test GSI changes on a new index, not the existing one.** Create a
  new GSI with the desired projection; verify queries work; then delete
  the old GSI. Never modify an in-use GSI directly (GSIs cannot be
  modified — only created or deleted).
- **Verify no consumers depend on Streams before disabling.** Lambda
  triggers on DynamoDB Streams will silently stop processing. Check
  event source mappings before disabling.
- **TTL takes up to 48 hours for the first deletes.** Do not expect
  immediate storage reduction. Monitor table size over 7 days.
- **Capacity mode switch from provisioned to on-demand is instant**
  but switching back requires specifying RCU/WCU. Ensure the rollback
  path is documented.
- **Auto-scaling changes can cause brief throttling.** Lowering
  min-capacity below the current consumed rate will cause throttling
  during the transition. Lower gradually.
- **Global Table replica changes require multi-region coordination.**
  Do not change capacity on a Global Table member without verifying
  replication health first.
- **Bulk-operation limit:** Process at most 5 tables per batch. Sort
  by estimated savings, verify each batch before proceeding. Abort if
  any table shows increased throttling or errors post-change.
