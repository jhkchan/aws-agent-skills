# Example usage: redshift-query-troubleshooter

A walkthrough showing the skill diagnosing a slow query caused by
distribution key skew (DS_DIST_ALL_INNER in EXPLAIN), demonstrating
the EXPLAIN-first methodology, the distribution-style-vs-join-column
analysis, the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the
ALTER DISTSTYLE remediation.

## Input (user prompt)

> Our sales analytics query started taking 45 seconds after we migrated
> the sales table to DISTSTYLE EVEN. The query joins sales to the store
> dimension table. EXPLAIN shows DS_DIST_ALL_INNER. Help us find the
> root cause.

```text
Cluster: prod-analytics-cluster
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

## Skill output

```text
TARGET: prod-analytics-cluster, query on analytics_db
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The query joins sales (DISTSTYLE EVEN, 800M rows) to store
  (DISTSTYLE KEY on store_id) on the store_id column. EXPLAIN shows
  DS_DIST_ALL_INNER -- the entire sales table is redistributed to all
  compute nodes because its EVEN distribution does not co-locate rows
  by store_id. The broadcast of 800M rows dominates the 44.2-second
  execution time.
LAYER: DIST_KEY_SKEW
EVIDENCE:
  - Symptom: query takes 45 seconds; EXPLAIN shows
    "XN Hash Join DS_DIST_ALL_INNER" followed by "XN Seq Scan on
    sales".
  - Probe: SVV_TABLE_INFO shows sales.diststyle = EVEN,
    store.diststyle = KEY(distkey: store_id). The join column
    (store_id) is not the dist key on sales.
  - Probe: EXPLAIN confirms DS_DIST_ALL_INNER -- the entire sales
    table is redistributed across all nodes at query time.
  - Passing: sales has a sort key on sale_date; the query does not
    filter on a date range so the sort key is not the bottleneck
    here (but should be reviewed for queries that do filter by date);
    the query uses a Hash Join (not a Nested Loop); no locks are
    present (STV_LOCKS empty); WLM queue time is 0.5s (not a WLM
    issue); the store dimension table (5,000 rows) is small enough
    that DISTSTYLE ALL would also work.
REMEDIATION:
  1. Change the sales table distribution to KEY on store_id to
     co-locate rows with the store dimension table:
     ALTER TABLE sales ALTER DISTSTYLE KEY DISTKEY (store_id);
  2. Run ANALYZE to update table statistics after the distribution
     change:
     ANALYZE sales;
  3. Re-run the query; EXPLAIN should show DS_DIST_NONE (no
     redistribution). Expected runtime: under 5 seconds for the
     broadcast elimination alone.
  4. For queries that also filter on sale_date, consider a compound
     sort key (sale_date, store_id) to preserve range scan
     performance after the distribution change.
CONFIRM: Before altering the table, emit and await:
  "CONFIRM: About to ALTER DISTSTYLE on sales (800M rows) to
   KEY(store_id). This requires a full table rewrite and will hold
   an exclusive lock for potentially 30-60 minutes. Schedule during
   a maintenance window. Proceed? (yes/no)"
  Do NOT run the SQL until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Read EXPLAIN first, never rewrote the SQL.** A generic assistant
   suggests query rewrites (subqueries, CTEs, join order changes). The
   skill's first probe is EXPLAIN, which immediately reveals
   `DS_DIST_ALL_INNER` -- a distribution problem, not a SQL structure
   problem. No query rewrite can fix a distribution mismatch.

2. **Identified the EVEN-vs-KEY mismatch with positive evidence.** The
   skill cross-references `SVV_TABLE_INFO` to confirm `sales.diststyle
   = EVEN` and `store.diststyle = KEY(distkey: store_id)`. The join
   column (store_id) is the dist key on `store` but not on `sales`,
   forcing the broadcast. This is specific, evidence-backed root cause
   identification.

3. **Ruled out WLM, locks, and sort keys.** The skill confirms
   `queue_time = 0.5s` (not WLM), `STV_LOCKS` is empty (not locks),
   and the sort key on sale_date is not the bottleneck for this
   query pattern (no date filter). Eliminating these layers with
   evidence narrows the diagnosis confidently.

4. **Recommended ALTER DISTSTYLE, not a query rewrite.** The primary
   remediation is `ALTER TABLE sales ALTER DISTSTYLE KEY (store_id)`.
   This fixes the root cause for ALL queries joining sales to store
   on store_id, not just this one query.

5. **Flagged the maintenance window implication.** The skill notes
   that ALTER DISTSTYLE on an 800M row table requires a full rewrite
   and exclusive lock for 30-60 minutes. A generic assistant omits
   this operational impact, potentially causing production disruption.

6. **Included a follow-up for sort key consideration.** The skill
   recommends reviewing the compound sort key after the distribution
   change, because the query also filters on `sale_date` in other
   workloads.

## Slash-command invocation

```
/aws:troubleshoot-redshift-query
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why the sales analytics query takes 45 seconds"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: redshift-query-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI or Data API)

After remediating, validate the query performance improvement:

```sql
-- Verify the distribution style was changed
SELECT schemaname, tablename, diststyle
FROM svv_table_info
WHERE tablename = 'sales';

-- Verify statistics are updated
ANALYZE sales;

-- Re-run EXPLAIN to confirm DS_DIST_NONE
EXPLAIN
SELECT s.store_name, sum(sa.amount)
FROM store s
JOIN sales sa ON s.store_id = sa.store_id
GROUP BY s.store_name;

-- Time the query
SELECT ... ; -- verify runtime drops below 5 seconds

-- Monitor WLM for queue contention after the fix
SELECT query, service_class,
       queue_time / 1000000 AS queue_secs,
       exec_time / 1000000 AS exec_secs
FROM stl_wlm_query
WHERE query = (
  SELECT MAX(query) FROM stl_query
  WHERE starttime >= CURRENT_DATE - INTERVAL '5 minutes'
);
```

Then monitor the query's execution time over the next few hours to
confirm consistent performance improvement across different data
volumes and concurrent workloads.
