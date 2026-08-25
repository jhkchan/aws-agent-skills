# Advanced Patterns — Transfer Family Cost Optimizer

Expert-knowledge deep dives, optimization signal tables, and recent features moved verbatim from SKILL.md. Loaded on demand.

## Mindset — four cost principles

Transfer Family cost optimization is a usage-pattern decision, not a
pure capacity-sizing exercise. The goal is the endpoint type,
concurrency, and workflow configuration that minimizes dollar cost
while preserving the file-transfer SLO — not the maximum concurrency
that the server can handle.

Four principles guide every recommendation:

- **Per-hour charges dominate for low-usage servers.** A server running
  24/7 at $0.30/hour costs $219/month even with zero transfers. Idle
  detection is the highest-leverage action for sporadic workloads.
- **Endpoint type compounds with NAT Gateway cost.** A VPC endpoint
  server that routes outbound through a NAT Gateway adds per-GB data
  processing on top of the per-hour surcharge. PUBLIC eliminates both.
- **Managed workflow cost is invisible until you count executions.**
  Step Functions charges per state transition. A multi-step workflow
  on every uploaded file multiplies cost linearly with file count.
- **Logging cost is a silent multiplier.** CloudWatch Logs ingest at
  ~$0.50/GB; a high-volume SFTP server can generate hundreds of GB of
  logs per month, exceeding the server cost itself.

## Step 0 — Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **PUBLIC is cheapest; VPC adds NAT cost.** A VPC endpoint server
  routing S3 access through a NAT Gateway incurs per-GB data processing
  ($0.045/GB) on top of the per-hour VPC surcharge. PUBLIC endpoints
  access S3 directly over the AWS network with no NAT overhead.
- **Idle servers charge per hour.** A server with zero sessions still
  incurs the full per-hour rate. The only way to stop the charge is to
  delete the server (configuration is lost) or accept the cost. For
  sporadic workloads, consider whether a serverless alternative (e.g.,
  S3 pre-signed URLs for occasional transfers) is viable.
- **Per-GB Transfer fee is on top of S3 data transfer.** Transfer
  Family charges a per-GB fee ($0.04/GB) for data transferred through
  the server. This is separate from S3 upload/download costs.
- **Managed workflow cost scales with file count.** A Step Functions
  managed workflow charges per execution. A 5-step workflow on 1M files
  = 5M state transitions. The cost is the same whether each file is 1
  KB or 1 GB.
- **CloudWatch Logs ingest is the silent cost multiplier.** SFTP
  logging generates one log event per file transfer operation. At
  $0.50/GB ingest, a server transferring 1M small files can generate
  200+ GB of logs per month — $100+ in logging cost alone.
- **FTP protocol is rarely available.** FTP (unencrypted) is supported
  only on VPC-type servers and is disabled by default. SFTP is the
  standard; FTPS adds TLS overhead. Protocol choice rarely affects
  cost directly but affects session duration and retry patterns.
- **Custom IdP Lambda charges per authentication.** Each SFTP login
  triggers a Lambda invocation via API Gateway. At high session-start
  rates, the Lambda + API Gateway cost compounds.
- **Concurrency limit is per-server, not per-user.** A server with
  `Protocols.Sftp.SessionPolicy` concurrency of 10 can handle 10
  concurrent sessions across ALL users. Spawning a second server to
  handle more is a cost decision vs increasing the concurrency limit.
- **Sticky sessions affect retry patterns.** If sticky sessions are
  configured, session reconnects target the same server. This can
  cause uneven load distribution, leading to over-provisioning.
- **Trusted host key rotation causes transient reconnects.** Rotating
  the host key invalidates cached client `known_hosts` entries. While
  rotation has no direct cost, the resulting retry storm can spike
  ConcurrentSessions and Lambda IdP invocations.

## Step 2 — Idle server options

**Idle server options:**
- **Delete the server** if the use case is decommissioned. This is
  the only way to fully eliminate the per-hour charge.
- **Migrate to serverless alternatives** (S3 pre-signed URLs, S3
  Access Points for occasional partner transfers) if the usage is
  sporadic and does not require the SFTP protocol.
- **Keep but document** if the server is required for compliance or
  partner connectivity even at low usage. Accept the cost as
  operational overhead.

## Step 3 — Protocol selection table

| Protocol | Cost impact | Notes |
|---|---|---|
| SFTP | Baseline | Default; most cost-efficient (single TCP connection, no TLS handshake) |
| FTPS | TLS overhead per session | Slightly longer session setup; negligible per-session cost impact |
| FTP | Only on VPC servers | Unencrypted; rare in practice. Requires VPC endpoint (higher cost). |

**Recommendation:** Use SFTP wherever the client supports it. FTPS is
acceptable if the partner requires it. FTP is almost never justified.

## Step 5 — Session duration checklist

Long sessions tie up concurrency slots without transferring files. A
user who connects and holds the session open for hours without
transferring data wastes concurrency capacity.

**Session duration checklist:**
| Symptom | Fix |
|---|---|
| Average session > 30 min AND few files per session | Investigate idle session hold; set session timeout |
| Sessions correlate with business hours only | Consider stopping the server outside business hours (VPC_ENDPOINT only) |
| Session count >> file transfer count | Users are connecting and disconnecting without transferring; audit user scripts |

## Step 7 — Logging optimization signals

**Logging optimization:**
| Signal | Recommendation |
|---|---|
| Log volume > 100 GB/month | Reduce log verbosity; log only errors and authentication events |
| Log group retention = Never expire | Set retention to 7-30 days; archive older logs to S3 |
| Every file operation logged at INFO | Change to WARNING or ERROR level; filter at the source |
| Logs used for audit compliance | Export to S3 (cheaper storage) and query via Athena |

## Step 8 — IdP optimization signals

**IdP optimization:**
| Signal | Recommendation |
|---|---|
| Sessions started > 50,000/month | Enable authentication caching in the Lambda (short-lived cache for repeated logins) |
| API Gateway cost dominates | Evaluate Lambda Function URL instead of API Gateway (cheaper per-request) |
| Lambda is cold-start heavy | Provisioned concurrency on the IdP Lambda (trade-off: provisioned cost vs latency) |
| Every file transfer triggers re-authentication | Investigate session reuse; SFTP should authenticate once per session, not per file |

## Recent AWS features (2024-2026)

## Recent AWS features (2024-2026)

- **Transfer Family managed workflows GA (2024-2025):** Step Functions-
  backed workflows triggered on file upload/download. Cost scales with
  file count × steps per workflow.
- **Transfer Family async (2025-2026):** Delegated authentication with
  caching, reducing per-authentication Lambda invocations for repeated
  logins.
- **Transfer Family web apps (2025):** AWS-managed web app for SFTP
  file transfer without a custom client. May reduce session duration
  for interactive users.
- **Improved CloudWatch metrics (2024):** `BytesIn`, `BytesOut`,
  `FilesIn`, `FilesOut`, `ConcurrentSessions`, `UserSessionsStarted`
  per server. Enables precise usage-pattern analysis.
- **Transfer Family directory listing optimization (2024-2025):**
  Reduced per-listing S3 ListObjects calls for large directories.
  Lowers indirect S3 request cost for browsing-heavy workloads.
- **VPC endpoint for Transfer Family (2024):** `VPC_ENDPOINT` type
  enables internal-only access without an internet gateway. Adds
  per-hour VPC endpoint fee but eliminates NAT Gateway requirement for
  internal-only servers.
- **S3 Access Points integration (2025):** Transfer Family home
  directory mappings can target S3 Access Points, simplifying multi-
  tenant server configurations.
