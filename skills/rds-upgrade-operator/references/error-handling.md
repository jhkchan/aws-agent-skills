# Error Handling — RDS and Aurora Engine Upgrade Operator


## Upgrade failure-mode table (use during diagnosis)

**Upgrade failure-mode table (use during diagnosis):**

| Symptom | Root cause | Fix |
|---|---|---|
| Upgrade fails immediately with `InvalidParameterCombination` | Target engine version not valid for the instance class or storage type | Check `describe-db-engine-versions --engine <engine> --db-instance-class <class>` for valid targets |
| Upgrade fails with `ParameterGroupNotFound` | No parameter group for the target engine family attached | Create a target-family param group and attach via `--db-parameter-group-name` |
| Upgrade fails with `OptionGroupNotFound` | No option group for the target engine family attached | Create a target-family option group and attach via `--option-group-name` |
| Instance stuck in `upgrade-failed` | Incompatible parameter or option, or insufficient storage | Review CloudWatch Logs and RDS events; the instance attempts auto-rollback. If stuck, PITR restore. |
| Application cannot connect after MySQL 8.0 upgrade | `caching_sha2_password` default not supported by old driver | Update driver, OR set `default_authentication_plugin = mysql_native_password` in the target param group |
| Application cannot connect after PostgreSQL upgrade | `pg_hba.conf` changes in the new version (stricter defaults) | Update the target param group `pg_hba.conf` entries; verify application IP ranges |
| Query performance regression after PostgreSQL upgrade | Planner statistics stale after `pg_upgrade` | Run `ANALYZE` on all tables; consider `VACUUM ANALYZE` for heavily updated tables |
| Aurora replicas lag after cluster upgrade | Replicas rebuilding from the upgraded writer | Monitor `AuroraReplicaLag`; wait for it to return to baseline |
| Global cluster secondary unreachable during upgrade | Secondary is being rebuilt from the upgraded primary | Plan for secondary Region downtime; consider a read traffic cutover before the upgrade |
