# Eval prompt: sortkey-misalignment-seq-scan

Diagnose the Redshift query performance issue for the following cluster.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: query on the `events` table takes 60 seconds. The table has
500 million rows and NO sort key. The query filters on `created_at` and
`event_type` but EXPLAIN shows a full `Seq Scan` (no zone map
elimination possible).

```text
Cluster: rs-redshift-sortkey-misalignment
Database: analytics_db
Query:
  SELECT event_type, count(*)
  FROM events
  WHERE created_at >= '2026-08-01'
    AND created_at < '2026-08-02'
    AND event_type = 'purchase'
  GROUP BY event_type;

Table definition:
  events:
    DISTSTYLE: KEY (distkey: user_id)
    sortkey: (none)
    rows: 500,000,000

EXPLAIN excerpt:
  XN Seq Scan on events
    Filter: ((created_at >= '2026-08-01') AND
             (created_at < '2026-08-02') AND
             (event_type = 'purchase'))

SVV_TABLE_INFO:
  tablename: events
  sortkey1: (empty)
  unsorted: N/A (no sort key)
  size: 125 GB

STL_WLM_QUERY: queue_time = 0.3s, exec_time = 59.5s
STV_LOCKS: empty
```

The query should only scan approximately 1 day of data (~1.4M rows out
of 500M) but without a sort key on `created_at`, Redshift cannot use
zone maps to skip blocks. The entire 500M row table is scanned on every
query execution.
