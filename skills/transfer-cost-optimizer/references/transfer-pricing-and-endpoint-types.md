# Transfer Family Pricing and Endpoint Types Reference

Supplementary reference for the Transfer Family Cost Optimizer skill.
Loaded on-demand when detailed pricing math, endpoint-type comparison,
concurrency reference, managed workflow cost model, CloudWatch Logs
cost model, or custom IdP Lambda cost model is needed.

## Transfer Family pricing (us-east-1, 2026, USD)

### Server hourly pricing

| Endpoint type | $/hour/server | Notes |
|---|---|---|
| PUBLIC | $0.30 | Cheapest; no VPC/NAT overhead. Clients connect over the public internet. |
| VPC | $0.30 + VPC infrastructure | Adds NAT Gateway ($0.045/GB outbound) + VPC hourly. Required for private connectivity or FTP protocol. |
| VPC_ENDPOINT | $0.30 + VPC endpoint hourly + per-GB | Internal-only access without internet gateway. Adds VPC endpoint per-hour + per-GB fees. |

### Data transfer pricing

| Component | Rate | Notes |
|---|---|---|
| Per-GB transferred (in or out) | $0.04/GB | Charged on data passing through the Transfer server. Separate from S3 upload/download costs. |
| S3 upload/download (underlying) | S3 standard rates | Transfer Family does not waive S3 data transfer; both costs apply. |
| NAT Gateway data processing (VPC only) | $0.045/GB | Applies to outbound traffic from VPC-type servers via NAT Gateway. Eliminated by PUBLIC. |

### Free tier

- Transfer Family does NOT have a free tier. All servers incur per-hour
  charges from creation.

### Duration billing precision

Transfer Family bills per hour per server. Partial hours are billed as
full hours in some regions — verify the current billing granularity on
the pricing page. Server deletion stops per-hour charges immediately.

## Endpoint type comparison

| Dimension | PUBLIC | VPC | VPC_ENDPOINT |
|---|---|---|---|
| Per-hour rate | $0.30 (baseline) | $0.30 + VPC infra | $0.30 + VPC endpoint |
| NAT Gateway cost | None | $0.045/GB outbound | None (no NAT needed) |
| Internet gateway required | Yes (AWS-managed) | Yes (customer VPC) | No |
| Client connectivity | Public internet | Public internet via VPC | Internal/VPC only |
| FTP protocol support | No | Yes (VPC only) | No |
| FTPS protocol support | Yes | Yes | Yes |
| SFTP protocol support | Yes | Yes | Yes |
| Use case | Partner file exchange over public internet | Private connectivity, FTP, or VPC-internal | Internal-only access without internet |

### When PUBLIC is the correct choice

- Clients connect from the public internet (partners, external users).
- No compliance requirement mandates VPC-internal access.
- FTP protocol is not required (SFTP/FTPS only).
- No NAT Gateway dependency for other VPC workloads.

### When VPC is the correct choice

- FTP protocol is required (VPC-only).
- Private connectivity via a customer VPC is a hard requirement.
- The server must route through a NAT Gateway or VPC routing table.

### When VPC_ENDPOINT is the correct choice

- Internal-only access (no public internet exposure).
- No internet gateway in the VPC.
- Clients connect from within the AWS network (peered VPC, Transit
  Gateway, Direct Connect).

## Protocol cost implications

| Protocol | Cost impact | Notes |
|---|---|---|
| SFTP | Baseline (single TCP connection, no TLS overhead) | Default; most cost-efficient. |
| FTPS | TLS handshake per session (~50-200 ms overhead) | Negligible per-session cost; slightly longer session setup. |
| FTP | VPC-only (forces VPC endpoint type) | Unencrypted; rare. The VPC requirement is the cost driver, not FTP itself. |

**Recommendation:** Use SFTP wherever possible. FTPS is acceptable if
the partner requires TLS. FTP is almost never cost-justified.

## Concurrency limit reference

| Server configuration | Max concurrent sessions | Notes |
|---|---|---|
| Default | 10 per server | Configurable via server settings. |
| High-concurrency | Up to 100 per server (region-dependent) | Requires AWS support limit increase. |
| Per-user | Configurable via session policy | Limits a single user's concurrent sessions. |

### Right-sizing gate

| Observed ConcurrentSessions | Configured limit | Action |
|---|---|---|
| p99 < 50% of limit | High over-provision | Reduce limit to p99 + 20% headroom |
| p99 > 90% of limit | Near saturation | Increase limit OR add a server |
| p99 ≈ 50-80% of limit | Right-sized | No change |

## Managed workflow Step Functions cost model

Managed workflows run Step Functions state machines on file upload/
download events. Cost scales with file count × steps per workflow.

### Pricing

| Step Functions type | Rate | Notes |
|---|---|---|
| Standard (per state transition) | $0.025 per 1,000 state transitions | Used by Transfer Family managed workflows |
| Express (per invocation) | $1.00 per 1M invocations + $0.00001667/GB-second | Not directly used by Transfer Family managed workflows |

### Cost formula

```
workflow_monthly_cost = files_per_month × steps_per_workflow × $0.025 / 1000
```

### Example scenarios

| Files/month | Steps per workflow | Monthly cost |
|---|---|---|
| 100,000 | 3 | $7.50 |
| 100,000 | 7 | $17.50 |
| 1,000,000 | 3 | $75.00 |
| 1,000,000 | 7 | $175.00 |
| 5,000,000 | 3 | $375.00 |
| 5,000,000 | 7 | $875.00 |

The cost scales linearly with file count — 1M small files cost the same
as 1M large files. This makes managed workflows disproportionately
expensive for high-volume small-file workloads.

### Optimization strategies

| Strategy | Saving | Trade-off |
|---|---|---|
| Combine steps (7 → 5) | ~29% workflow cost reduction | Less granular step-level error handling |
| Move validation to S3 Event + Lambda | Eliminates workflow for validation-only steps | Lambda per-invocation cost; no state machine |
| Batch files before workflow trigger | Reduces execution count by batch factor | Adds latency (batch window) |
| Remove unused retry steps | Reduces steps per workflow | Less resilient to transient failures |

## CloudWatch Logs cost model

SFTP logging generates one log event per file transfer operation.

### Pricing

| Component | Rate | Notes |
|---|---|---|
| Ingest | $0.50/GB | First 5 GB/month free |
| Storage | $0.03/GB/month | First 5 GB/month free |
| Insights queries | $0.005/GB scanned | Per-query cost for CloudWatch Logs Insights |

### Cost formula

```
logs_monthly_cost = (log_GB_per_month × $0.50)    [ingest]
                    + (log_GB_per_month × $0.03)    [storage, first 5 GB free]
```

### Log volume estimation

| Files transferred/month | Log level | Estimated GB/month |
|---|---|---|
| 100,000 | INFO | ~10 GB |
| 100,000 | WARNING | ~2 GB |
| 1,000,000 | INFO | ~100 GB |
| 1,000,000 | WARNING | ~20 GB |
| 5,000,000 | INFO | ~500 GB |
| 5,000,000 | WARNING | ~100 GB |

Reducing from INFO to WARNING typically cuts log volume by ~80%.

### Optimization strategies

| Strategy | Saving | Trade-off |
|---|---|---|
| Reduce log level (INFO → WARNING) | ~80% log volume reduction | Loses per-file INFO-level audit trail |
| Set retention (7-30 days) | Eliminates long-term storage cost | Must archive to S3 if long-term retention required |
| Export to S3 + Athena | $0.023/GB S3 storage vs $0.03/GB CloudWatch | Adds export pipeline complexity |
| Filter at source | Only log authentication + errors | Loses per-file transfer visibility |

## Custom identity provider Lambda cost model

Custom identity providers (API_GATEWAY type) invoke a Lambda function on
every SFTP authentication.

### Pricing

| Component | Rate | Notes |
|---|---|---|
| Lambda invocation | $0.0000002/request (first 1M free) | Plus compute time ($0.0000166667/GB-second) |
| API Gateway request | $3.00 per 1M requests (HTTP API) | REST API is more expensive ($3.50/M) |

### Cost formula

```
idp_monthly_cost = sessions_started_per_month
                   × (lambda_per_invocation + lambda_compute + apigw_per_request)
```

### Example scenarios

| Sessions started/month | Lambda cost | API Gateway cost | Total IdP cost/month |
|---|---|---|---|
| 10,000 | ~$1.00 | ~$0.03 | ~$1.03 |
| 50,000 | ~$5.00 | ~$0.15 | ~$5.15 |
| 80,000 | ~$8.00 | ~$0.24 | ~$8.24 |
| 200,000 | ~$20.00 | ~$0.60 | ~$20.60 |

### Optimization strategies

| Strategy | Saving | Trade-off |
|---|---|---|
| Enable auth caching (short-lived cache for repeated logins) | Reduces invocations by 50-90% for repeated logins | Cache invalidation complexity |
| Switch from API Gateway to Lambda Function URL | Eliminates API Gateway cost | Loses API Gateway features (throttling, WAF) |
| Provisioned concurrency on IdP Lambda | Eliminates cold-start latency | Adds provisioned concurrency cost |
| Session reuse (SFTP authenticates once per session) | No change if already once-per-session | N/A |

## Regional pricing multipliers

| Region | Multiplier vs us-east-1 |
|---|---|
| us-east-1, us-west-2, eu-west-1 | 1.0x (baseline) |
| ap-southeast-1, ap-northeast-1 | ~1.1x |
| ap-south-1 | ~1.15x |
| sa-east-1 | ~1.2x |
| us-gov-west-1 | ~1.5x (verify on pricing page) |

Always re-state the regional rate from the Transfer Family pricing page
for regions outside us-east-1; the multipliers adjust periodically.

## CLI command reference

### Inspect server configuration

```bash
# Server details
aws transfer describe-server --server-id <id>

# List users
aws transfer list-users --server-id <id>

# Describe a specific user
aws transfer describe-user --server-id <id> --user-name <name>

# List managed workflows
aws transfer list-workflows

# Describe a workflow
aws transfer describe-workflow --workflow-id <id>
```

### Inspect metrics

```bash
# ConcurrentSessions (14-30 day window)
aws cloudwatch get-metric-statistics --namespace AWS/Transfer \
  --metric-name ConcurrentSessions \
  --dimensions Name=ServerId,Value=<id> \
  --start-time $(date -d '-30 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum,Sum --output json

# FilesIn / FilesOut
aws cloudwatch get-metric-statistics --namespace AWS/Transfer \
  --metric-name FilesIn \
  --dimensions Name=ServerId,Value=<id> \
  --start-time $(date -d '-30 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 86400 --statistics Sum --output json

# UserSessionsStarted
aws cloudwatch get-metric-statistics --namespace AWS/Transfer \
  --metric-name UserSessionsStarted \
  --dimensions Name=ServerId,Value=<id> \
  --start-time $(date -d '-30 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 86400 --statistics Sum --output json
```

### Apply changes

```bash
# Create a new PUBLIC server
aws transfer create-server \
  --endpoint-type PUBLIC \
  --protocols SFTP \
  --identity-provider-type SERVICE_MANAGED \
  --region us-east-1

# Create a user on the new server
aws transfer create-user \
  --server-id <new-id> \
  --user-name <user> \
  --ssh-public-key-body <key> \
  --home-directory /<bucket>/<user>

# Update logging role (reduce verbosity at source)
aws transfer update-server \
  --server-id <id> \
  --logging-role arn:aws:iam::<acct>:role/TransferLogging

# Create a simplified workflow
aws transfer create-workflow \
  --steps <simplified-steps-json>

# Delete an old server (after migration confirmed)
aws transfer delete-server --server-id <old-id>
```

### Cost Explorer Transfer spend

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-07-11,End=2026-08-11 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Transfer"]}}' \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE
```

## Extended anti-patterns

1. **NEVER migrate from VPC to PUBLIC without verifying all clients can
   reach the server over the public internet.** Internal-only partners
   or compliance requirements may block PUBLIC migration.
2. **NEVER delete a server without preserving user configurations and
   S3 home directories.** `delete-server` is irreversible.
3. **NEVER simplify a managed workflow without auditing each step.**
   Removing a validation or transformation step may break downstream
   processes.
4. **NEVER reduce log verbosity without confirming the audit/compliance
   requirements.** Some regimes mandate full file-transfer logging.
5. **NEVER consolidate servers without verifying the combined peak fits
   within a single server's concurrency limit.** Over-consolidation
   causes session rejection during peak hours.
6. **NEVER assume per-GB rates are flat across regions.** Always re-
   state the regional rate from the pricing page.

## Endpoint-type decision tree

```
Do clients connect from the public internet?
├── YES → Is FTP protocol required?
│   ├── NO → Use PUBLIC (cheapest, no NAT overhead)
│   └── YES → Use VPC (FTP requires VPC)
└── NO (internal/VPC only)
    ├── Is an internet gateway available?
    │   ├── YES → Use VPC
    │   └── NO → Use VPC_ENDPOINT
    └── Is Direct Connect / peering the access path?
        └── Use VPC_ENDPOINT
```

## Server-count vs concurrency decision tree

```
Combined peak ConcurrentSessions across all servers:
├── < single-server concurrency limit (10)
│   └── Consolidate to 1 server (save (N-1) × $0.30 × 730/month)
├── ≈ single-server limit
│   └── Keep on 1 server; increase limit to p99 + 20% headroom
└── > single-server limit
    ├── Can the limit be increased (AWS support)?
    │   ├── YES → Increase limit; consolidate
    │   └── NO → Keep N servers but right-size each (p99 + 20% headroom)
    └── Evaluate sticky session necessity (uneven load → over-provisioning)
```
