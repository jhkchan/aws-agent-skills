# Baseline (no-skill) — oracle-source-binary-reader-ssl

> This is the response a model produces **without** the skill
> definition. It creates the Oracle endpoint but misses the Binary
> Reader configuration (useLogminerReader=N, AdditionalArchivedLogDestId),
> the supplemental logging prerequisite, the verify-full SSL requirement
> with imported certificate, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

To create a DMS Oracle source endpoint:

1. Create an Oracle source endpoint in DMS.
2. Enter the server, port, and SID.
3. Provide the Oracle username and password.
4. Enable SSL if needed.

```bash
aws dms create-endpoint --engine-name oracle --server-name oracle-prod \
  --port 1521 --database-name ORCL
```

DMS will use LogMiner by default for CDC.
