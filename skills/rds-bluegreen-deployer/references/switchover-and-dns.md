# Switchover and DNS — RDS Blue/Green Deployer

Deep reference on switchover mechanics (replication drain, endpoint
rename, downtime characteristics), DNS/endpoint behavior (CNAME
swap, application connection implications), switchover timeout
tuning, and rollback scenarios. Loaded on demand by the skill —
kept out of the main SKILL.md body so the deployment procedure stays
scannable.

## Switchover mechanics

### What happens during switchover

Switchover is the process of promoting green to production and
demoting blue to staging. The operation happens in three phases:

```text
Phase 1: Replication drain (~1-5 seconds)
  → Blue → green logical replication is stopped
  → Any in-flight replicated transactions are applied to green
  → Green is now a consistent point-in-time copy of blue
  → No application impact yet

Phase 2: Endpoint rename (~1-10 seconds)
  → Blue CNAME: prod-db.cluster-xxx.rds.amazonaws.com
     BEFORE → points to blue instance
     AFTER  → points to green instance (new production)
  → Green CNAME: green-prod-db.cluster-xxx.rds.amazonaws.com
     BEFORE → points to green instance
     AFTER  → points to blue instance (former production, now staging)
  → DNS TTL is very short (usually < 5 seconds)

Phase 3: Application reconnection (~0-60 seconds)
  → New connections resolve the CNAME and connect to the new production
  → Existing (long-lived) connections are BROKEN and must reconnect
  → Applications with retry: sub-second blip
  → Applications without retry: visible downtime (up to DNS TTL + reconnect)
```

### Switchover is NOT truly zero-downtime

The official documentation describes Blue/Green switchover as having
"typically less than one minute" of downtime. The actual downtime
depends on:

| Factor | Impact | Mitigation |
|---|---|---|
| DNS propagation | 1-10 seconds typically | Short DNS TTL on RDS endpoints |
| Connection pool refresh | Existing connections break | Use connection pooling with retry |
| Application retry logic | No retry = visible errors | Implement exponential backoff retry |
| DNS caching on app servers | Stale cache = wrong endpoint | Flush DNS cache post-switchover |
| Long-running transactions on blue | Drain time increases | Quiesce writes before switchover |

**Best practice:** reduce write load on blue for 30 seconds before
switchover. This reduces replication drain time and minimizes the
switchover window.

### Initiating switchover

```bash
# Switchover with default timeout (300 seconds)
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier bg-prod-upgrade-2026 \
  --region us-east-1

# Switchover with custom timeout (600 seconds for medium databases)
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier bg-prod-upgrade-2026 \
  --switchover-timeout 600 \
  --region us-east-1
```

### Monitoring switchover progress

```bash
# Check switchover status
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier bg-prod-upgrade-2026 \
  --query 'BlueGreenDeployments[0].Status' \
  --region us-east-1

# Status transitions:
#   PROVISIONING → green is being created
#   AVAILABLE → green is ready, waiting for switchover
#   SWITCHOVER_IN_PROGRESS → switchover is running
#   SWITCHOVER_COMPLETED → switchover done, green is now production
#   SWITCHOVER_FAILED → switchover failed, rolled back to blue
```

## DNS and endpoint behavior

### How the CNAME swap works

RDS uses DNS CNAME records for database endpoints. During switchover,
the CNAME records are swapped:

```text
BEFORE switchover:
  prod-mysql-db.cluster-cnfxxx.us-east-1.rds.amazonaws.com
    └── CNAME → blue-instance-cnfxxx.us-east-1.rds.amazonaws.com (PRODUCTION)

  green-prod-mysql-db.cluster-cnfxxx.us-east-1.rds.amazonaws.com
    └── CNAME → green-instance-cnfxxx.us-east-1.rds.amazonaws.com (STAGING)

AFTER switchover:
  prod-mysql-db.cluster-cnfxxx.us-east-1.rds.amazonaws.com
    └── CNAME → green-instance-cnfxxx.us-east-1.rds.amazonaws.com (PRODUCTION!)

  green-prod-mysql-db.cluster-cnfxxx.us-east-1.rds.amazonaws.com
    └── CNAME → blue-instance-cnfxxx.us-east-1.rds.amazonaws.com (now STAGING)
```

**Key insight:** the application connection string does NOT change.
Applications using the prod endpoint CNAME automatically follow to
the new production (former green) after DNS propagation.

### Applications that need attention

| Application type | Issue | Action |
|---|---|---|
| Uses RDS endpoint CNAME | No issue — auto-follows | None |
| Hardcoded instance endpoint | Wrong after switchover | Update to use CNAME |
| Hardcoded IP address | Wrong after switchover | Use DNS endpoint, not IP |
| Long-lived connections | Broken at switchover | Implement reconnect with retry |
| DNS caching (JVM, OS) | Stale cache delays follow | Flush DNS cache or use low TTL |
| Connection pool (HikariCP, pgBouncer) | Pool may hold stale connections | Set maxLifetime < DNS TTL, or force pool reload |

### Verifying endpoint after switchover

```bash
# Resolve the production endpoint — should point to the new instance
dig prod-mysql-db.cluster-cnfxxx.us-east-1.rds.amazonaws.com +short

# Or check via the RDS API
aws rds describe-db-instances \
  --db-instance-identifier prod-mysql-db \
  --query 'DBInstances[0].{Endpoint:Endpoint,EngineVersion:EngineVersion}' \
  --region us-east-1
# EngineVersion should now show the target version (8.0)
```

## Switchover timeout tuning

### Default and range

| Parameter | Value |
|---|---|
| Default timeout | 300 seconds (5 minutes) |
| Minimum timeout | 30 seconds |
| Maximum timeout | 3600 seconds (1 hour) |

### Sizing the timeout

```text
Database size          Recommended timeout
─────────────────────  ──────────────────────
< 100 GB               300 seconds (default)
100 GB – 1 TB           600 seconds
1 TB – 5 TB             1800 seconds (30 minutes)
> 5 TB                  3600 seconds (1 hour)
```

### What happens on timeout

If the switchover does not complete within the timeout:
1. The switchover is rolled back.
2. Blue remains production (no changes).
3. Green remains in its pre-switchover state.
4. The Blue/Green Deployment status returns to `AVAILABLE`.
5. You can retry the switchover with a longer timeout.

**Rollback is safe:** the blue database is untouched. No data loss.

## Rollback scenarios

### Switchover fails

If switchover fails (timeout, error), blue remains production. The
Blue/Green Deployment stays in `AVAILABLE` status. You can:
- Fix the issue (e.g., reduce write load, increase timeout).
- Retry the switchover.

### Post-switchover rollback (manual)

After a successful switchover, there is no automatic rollback. The
former blue is now the new green. To roll back manually:
1. The former blue (new green) is still running.
2. Create a NEW Blue/Green Deployment with the former green (now
   blue/production) as the source, targeting the former blue (now
   green) engine version.
3. Switch over again.

**This is expensive and time-consuming.** Validate green thoroughly
before the initial switchover to avoid needing a rollback.

## Common switchover pitfalls

### Pitfall 1: High replication lag during switchover

If blue is under heavy write load, replication lag can be high. The
switchover must drain all replicated changes before swapping
endpoints, which extends downtime.

**Fix:** reduce write load on blue for 30-60 seconds before
switchover. Check lag via the Blue/Green status before initiating.

### Pitfall 2: Application DNS cache

Applications that cache DNS (JVM default cache, OS-level nscd/systemd-
resolved) may continue connecting to the old endpoint for seconds or
minutes after the CNAME swap.

**Fix:** configure low DNS TTL in the application runtime. Flush DNS
cache on application servers after switchover. For JVM-based apps,
set `networkaddress.cache.ttl=1` in java.security.

### Pitfall 3: Connection pool holding stale connections

Connection pools (HikariCP, c3p0, pgBouncer) maintain long-lived
connections that do not re-resolve DNS. After the CNAME swap, these
connections still point to the old instance.

**Fix:** set `maxLifetime` on the connection pool to be shorter than
the expected DNS propagation time, or trigger a pool flush after
switchover. For pgBouncer, use `RELOAD` to force reconnect.

## Terraform switchover example

```hcl
resource "aws_rds_blue_green_deployment" "upgrade" {
  blue_green_deployment_name = "bg-prod-upgrade-2026"
  source                     = aws_rds_cluster.prod.arn
  target_engine_version      = "8.0.mysql_aurora.3.04.0"
  target_db_parameter_group_name = aws_db_parameter_group.mysql80.name

  timeouts {
    create  = "120m"
    delete  = "120m"
    update  = "120m"
  }
}

# Switchover (run via terraform apply after validation)
resource "null_resource" "switchover" {
  triggers = {
    bg_id = aws_rds_blue_green_deployment.upgrade.id
  }

  provisioner "local-exec" {
    command = <<-EOT
      aws rds switchover-blue-green-deployment \
        --blue-green-deployment-identifier ${aws_rds_blue_green_deployment.upgrade.id} \
        --switchover-timeout 600 \
        --region us-east-1
    EOT
  }

  depends_on = [aws_rds_blue_green_deployment.upgrade]
}
```

---

## Step 7 — Switchover timeout configuration (moved from SKILL.md)

The switchover timeout controls how long the switchover operation can
run before it is rolled back. Default is 300 seconds (5 minutes).

```bash
# Set switchover timeout (e.g., 600 seconds for large databases)
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier "$BG_ID" \
  --switchover-timeout 600 \
  --region us-east-1
```

**Timeout guidance:**
- Small databases (< 100 GB): 300 seconds (default) is sufficient.
- Medium databases (100 GB – 1 TB): 600 seconds.
- Large databases (> 1 TB): 1800 seconds (30 minutes).
- If switchover times out, it rolls back — blue remains production.

## Step 8 — Application connection string update (moved from SKILL.md)

**The key benefit of Blue/Green:** applications using the RDS
endpoint CNAME do NOT need connection string changes. The DNS switch
is transparent.

```text
Before switchover:
  prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com → BLUE (production)
  green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com → GREEN (staging)

After switchover:
  prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com → GREEN (now production!)
  green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com → BLUE (now staging)

Application using prod-mysql-db endpoint: NO CHANGE NEEDED
```

**Applications that need attention:**
- Applications with hardcoded IP addresses (not using the DNS
  endpoint): MUST update the IP after DNS propagation.
- Applications with long-lived connections: MUST reconnect after
  switchover (connection retry logic handles this).
- Applications with DNS caching: flush DNS cache after switchover.

