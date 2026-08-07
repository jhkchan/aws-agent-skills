# Baseline (no-skill) response: cross-account-rotation-access-denied-blocked

This file captures what a generic assistant produces WITHOUT the
secrets-rotation-operator skill loaded.

---

The rotation Lambda is failing with `AccessDeniedException`. Since this
is a cross-account setup, you'll need to make sure the resource policies
are configured on both sides. Check that the Lambda resource-based policy
allows Secrets Manager to invoke the function. You may need to add a
permission:

```bash
aws lambda add-permission \
  --function-name SharedApikeyRotationLambda \
  --statement-id SecretsManagerAccess \
  --principal secretsmanager.amazonaws.com \
  --action lambda:InvokeFunction
```

After updating the policy, trigger a manual rotation to test.
