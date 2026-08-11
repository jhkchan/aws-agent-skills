# Baseline (no-skill) response: query-rewrite-select-star

This file captures what a generic assistant produces WITHOUT the
athena-query-optimizer skill loaded.

---

Your queries are using SELECT * which reads all columns even when you only
need a few. This is wasteful. You should change your queries to only select
the columns you need.

Also, you're not filtering by the partition column (dt), so every query
scans the entire table. Adding a WHERE clause on dt will significantly
reduce the amount of data scanned.

For the COUNT(DISTINCT), you could try using APPROX_COUNT_DISTINCT instead
which is faster. And add a LIMIT to your ORDER BY queries.
