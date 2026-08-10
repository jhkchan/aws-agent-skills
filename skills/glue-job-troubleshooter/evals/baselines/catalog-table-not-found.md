# Baseline (no-skill) response: catalog-table-not-found

This file captures what a generic assistant produces WITHOUT the
glue-job-troubleshooter skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT + CATEGORY, cross-account
IAM probe, distinguishes table-missing from permission-missing).

---

Your Glue job says "Table sales_raw not found" but it sounds like the
table does exist. Check that the table name is spelled correctly and
that the database name `analytics_prod` is right. Sometimes the table
gets deleted or the crawler hasn't run yet — try re-running the crawler.

Also, since this is a cross-account setup, make sure your Glue job's
IAM role has permission to read from the catalog in account
111122223333.
