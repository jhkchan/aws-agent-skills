# Baseline (no-skill) response: target-fk-constraint-violation-failed

This file captures what a generic assistant produces WITHOUT the
dms-task-troubleshooter skill loaded.

---

Your DMS task TASK003 failed at the ORDERS table with a foreign key
constraint violation. This means the orders table has a reference to
the customers table that couldn't be resolved.

You should remove the foreign key constraint from the target table and
try again, or make sure the customers table is loaded first.
