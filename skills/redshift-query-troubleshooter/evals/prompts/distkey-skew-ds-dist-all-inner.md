# Eval prompt: distkey-skew-ds-dist-all-inner

Diagnose the Redshift query performance issue for the following cluster.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: query on the analytics database takes 45 seconds. The query
joins the `sales` fact table (800 million rows) to the `store` dimension
table (5,000 rows). EXPLAIN output shows `DS_DIST_ALL_INNER` on the
join, indicating the sales table is redistributed to every node.

```text
Cluster: rs-redshift-distkey-skew
Database: analytics_db
Query:
  SELECT s.store_name, sum(sa.amount)
  FROM store s
  JOIN sales sa ON s.store_id = sa.store_id
  GROUP BY s.store_name;

Table definitions:
  sales:
    DISTSTYLE: EVEN
    sortkey: sale_date
    rows: 800,000,000
  store:
    DISTSTYLE: KEY (distkey: store_id)
    sortkey: store_id
    rows: 5,000

EXPLAIN excerpt:
  XN Hash Join DS_DIST_ALL_INNER
    -> XN Seq Scan on sales sa
    -> XN Hash -> XN Seq Scan on store s

STL_WLM_QUERY: queue_time = 0.5s, exec_time = 44.2s
STV_LOCKS: empty (no locks)
```

The `DS_DIST_ALL_INNER` signal in EXPLAIN indicates the sales table
(EVEN distribution) must be redistributed to all nodes at query time
because its rows are not co-located with the store table (KEY on
store_id). The fix is to change the sales table distribution to KEY on
store_id.
