# Baseline (no-skill) — jdbc-crawler-connection

> This is the response a model produces **without** the skill
> definition. It creates the JDBC crawler but misses the Glue
> Connection network requirements (VPC/subnet/SG must match the
> database), the connection test step, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the crawler:

```bash
aws glue create-crawler --name pg-crawler \
  --role GlueJdbcCrawlerRole \
  --database-name jdbc_db \
  --targets '{"JdbcTargets":[{"ConnectionName":"pg-connection","Path":"public/%"}]}'
```
