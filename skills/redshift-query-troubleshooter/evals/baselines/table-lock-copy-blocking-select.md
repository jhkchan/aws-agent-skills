# Baseline (no-skill) response: table-lock-copy-blocking-select

---

Your SELECT query is hanging because there's a lock on the table. It
looks like a COPY command is running on the same table and has an
exclusive lock. You need to wait for the COPY to finish or kill it.

To check what's blocking the query, look at the STV_LOCKS table. You
can use pg_terminate_backend to kill the blocking process if needed.

To avoid this in the future, try running your COPY and SELECT queries
at different times or use separate staging tables for loading data.
