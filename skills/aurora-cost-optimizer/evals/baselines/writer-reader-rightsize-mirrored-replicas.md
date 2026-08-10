# Baseline (no-skill) response: writer-reader-rightsize-mirrored-replicas

This file captures what a generic assistant produces WITHOUT the
aurora-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, writer vs reader
independent right-sizing, failover-aware reader sizing, anti-pattern:
don't downsize below failover-promotion size).

---

Your Aurora cluster has a writer and two readers all on db.r6g.2xlarge
but CPU usage is low across the board (15% on writer, ~8% on readers).
You can probably downsize. Try moving the writer to db.r6g.xlarge and
the readers to db.r6g.large to save some money.

Be sure to test failover after the change.
