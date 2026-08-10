# Baseline (no-skill) — symmetric-data-encryption

> This is the response a model produces **without** the skill definition.
> It produces a basic create-key command but misses the separated key
> administrators vs. key users principle (often granting the admin role
> Encrypt/Decrypt), the root break-glass statement, the explicit alias
> creation step, and the structured checklist.

---

Here's how to create your KMS key:

```bash
aws kms create-key \
  --description "Payments CMK for data encryption" \
  --policy file://policy.json
```

In the policy, grant the kms-admin role `kms:*` and the payments-svc
role `kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey*`.

After creating the key, you can create an alias if you want a
friendly name.

To enable rotation, go to the console or run:
`aws kms enable-key-rotation --key-id <key-id>`.
