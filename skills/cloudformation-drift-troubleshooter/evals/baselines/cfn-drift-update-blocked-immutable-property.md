# Baseline (no-skill) response: cfn-drift-update-blocked-immutable-property

This file captures what a generic assistant produces WITHOUT the
cloudformation-drift-troubleshooter skill loaded.

---

Your `orders-db-stack` is drifted because the RDS instance was
renamed from `orders-db-prod` to `orders-db-prod-v2`. To clear the
drift, update your template to use the new name and run
`aws cloudformation update-stack`.

Be careful — the `DBInstanceIdentifier` is an important property. You
might want to test with a changeset first to see what CloudFormation
will do.

If the rename was a mistake, you can rename it back using
`aws rds modify-db-instance`.
