# Baseline (no-skill) response: full-portfolio-assessment

This file captures what a generic assistant produces WITHOUT the
migration-hub-strategy-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, discovery trade-off
analysis, 6R classification context, anti-pattern detection, wave
sequencing from dependency data).

---

To assess your migration portfolio, you can use AWS Migration Hub
Strategy Recommendations. First, deploy the Discovery Collector on your
vCenter to gather inventory data. Then install agents on your servers
for more detailed information.

After collecting data for a couple of weeks, run the assessment from
the Migration Hub console. It will classify each server into one of the
6R strategies (rehost, replatform, refactor, repurchase, retain, retire).

For the servers running Windows Server 2012 R2, you should plan to
upgrade the OS during migration. For the Oracle 11g database, consider
moving to Aurora PostgreSQL using DMS.

You can use MGN for the rehost servers and DMS for the database
migration. Make sure to set up the service roles and replication
instances before starting.
