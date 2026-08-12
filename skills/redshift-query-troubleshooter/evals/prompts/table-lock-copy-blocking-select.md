# Eval prompt: table-lock-copy-blocking-select

Diagnose the Redshift query hang for the following cluster. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: a reporting SELECT query on the `orders` table has been
hanging for 10 minutes. The query started at 14:10 UTC; at 14:05 UTC a
large COPY began loading data into the same table.

```text
Cluster: rs-redshift-table-lock
Database: analytics_db

STV_LOCKS output:
  relation  | relname  | pid  | granted | lock_mode           | lock_owner_pid
  167854    | orders    | 8421 | true    | AccessExclusiveLock | (self)
  167854    | orders    | 8432 | false   | AccessShareLock     | 8421

STV_INFLIGHT output:
  pid  | query                                                  | starttime          | elapsed
  8421 | COPY orders FROM 's3://etl-bucket/huge_batch.csv' ... | 2026-08-11 14:05:00 | 620s
  8432 | SELECT count(*) FROM orders WHERE order_date = '...'    | 2026-08-11 14:10:00 | 320s
```

The COPY (pid 8421) holds an `AccessExclusiveLock` on the `orders`
table (granted = true). The SELECT (pid 8432) is waiting for an
`AccessShareLock` (granted = false), blocked by pid 8421. The SELECT
will not execute until the COPY completes or is terminated.
