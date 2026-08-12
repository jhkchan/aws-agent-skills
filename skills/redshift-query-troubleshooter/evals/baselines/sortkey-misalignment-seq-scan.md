# Baseline (no-skill) response: sortkey-misalignment-seq-scan

---

Your query is slow because it's scanning a large table. The EXPLAIN
shows a Seq Scan which means the entire table is being read. For a
500 million row table, that's going to be slow.

Some things to try:
- Add a sort key on the filter columns to speed up the scan
- Filter the data more aggressively with WHERE conditions
- Consider partitioning the data by date
- Use a materialized view for common query patterns

You should also check if the table statistics are up to date by
running ANALYZE.
