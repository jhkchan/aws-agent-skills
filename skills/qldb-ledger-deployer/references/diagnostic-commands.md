# Diagnostic Commands — QLDB Ledger Deployer

Diagnostic and monitoring reference material moved out of the SKILL.md body. Loaded on demand.


## Step 12 — CloudWatch metrics

| Metric | What it measures | Alert threshold |
|---|---|---|
| CommandExecutionLatency | PartiQL execution time | > 1000ms sustained |
| JournalStorage | Journal size (bytes) | Trending up rapidly |
| ReadIOs | Read I/O count | Spike = unindexed queries |
| WriteIOs | Write I/O count | Monitor write throughput |
| OccConflictExceptions | Optimistic concurrency conflicts | > 5% of commits |

**Key alert:** `OccConflictExceptions` > 5% of commits indicates
concurrent writes to the same document. Redesign the workload.
