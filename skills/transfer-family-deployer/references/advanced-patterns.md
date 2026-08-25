# Advanced patterns — transfer-family-deployer

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Transfer Family limits (2026)

**Transfer Family limits (2026):**

- Servers per account (default): 100 (soft limit, raisable).
- Users per server: 5000 (Service Managed); Directory Service: governed
  by the directory size.
- Concurrent files per server: governed by instance capacity (default
  sizing auto-scales).
- Tags per server: 50.
- AS2 messages per server: unlimited (subject to throughput limits).
- VPC endpoint servers per VPC: soft limit, raisable via Support.

### Step 0: Expert knowledge — non-obvious Transfer Family behaviors

These behaviors are easy to misjudge without operational Transfer
Family experience. Each changes a plan if ignored:

- **Protocols gate the endpoint type.** Plain FTP REQUIRES a VPC or
  VPC_ENDPOINT (never PUBLIC). FTPS supports any endpoint type but
  PUBLIC FTPS still leaks metadata. SFTP over PUBLIC is acceptable but
  VPC is preferred for partner B2B. AS2 only supports VPC/VPC_ENDPOINT.

- **IAM role = max scope; session policy = effective scope.** The
  Transfer Family service assumes the IAM role on behalf of the user
  for every S3 operation. The session policy (passed via `--policy` on
  `create-user` or returned by the custom IdP) is intersected with the
  role's identity-based policies to produce the effective permission
  set. Always pass a session policy that scopes the user to their home
  directory.

- **HomeDirectoryType: LOGICAL vs PATH.** `PATH` is the literal S3
  prefix. `LOGICAL` lets you map virtual directories to different S3
  prefixes via `HomeDirectoryMappings` — useful for chroot-like
  isolation. Default is `PATH`; use `LOGICAL` only when you need
  multi-folder mappings.

- **Service Managed users use SSH keys, not passwords.** Each user
  is created with `--ssh-public-key-body` (an SSH public key in
  OpenSSH format). Passwords are not supported for Service Managed
  SFTP users — rotate keys, not passwords.

- **Custom IdP response shape is non-negotiable.** The Lambda behind
  the API Gateway must return JSON with at minimum: `Role` (IAM ARN),
  `HomeDirectory` (S3 prefix), and optionally `Policy` (session policy
  JSON string), `HomeDirectoryType`, `PublicKeys`. Missing fields cause
  silent auth failures.

- **Directory Service SFTP uses AD credentials.** Users sign in with
  their `DOMAIN\username` and AD password — no SSH keys. The Directory
  Service must be a Managed Microsoft AD in the same VPC. Simple AD is
  not supported.

- **FTPS requires an ACM cert in the server's region.** The cert's
  subject MUST match the FTPS hostname clients connect to. Wildcard
  certs work for subdomains. Self-signed certs are technically
  supported but rejected by most client SFTP libraries.

- **VPC endpoint servers create an ENI in your VPC.** Clients connect
  to the ENI's private IP. You control networking (security groups,
  route tables, DNS). VPC_ENDPOINT (newer) lets you attach the server
  to your VPC without provisioning an ENI per subnet — preferred for
  multi-AZ resilience.

- **Logging role writes structured logs to CloudWatch.** Each
  user-level operation (upload, download, list, mkdir) is logged with
  a structured JSON payload. Without a `LoggingRole`, no audit trail.

- **AS2 uses local and partner profiles.** AS2 (RFC 4130) is B2B
  app-level file exchange over HTTP. Each partner needs a local profile
  (private key in Secrets Manager) and a partner profile (partner's
  cert). MDN (Message Disposition Notification) is asynchronous by
  default.

- **Managed workflows fire on partial or complete upload.**
  `OnPartialUpload` fires when bytes are received (chunked transfers).
  `OnUpload` fires when the file is fully written. Each workflow step
  is a Lambda, EKS task, or service step (copy, delete, tag). Workflows
  run in order; a failure can retry, abort, or continue.

- **Tags propagate for cost allocation.** Tag the server, not users.
  Tags like `Environment=prod` and `Partner=acme` flow through to
  Cost Explorer for chargeback.

- **Server endpoint DNS resolves after creation.** For PUBLIC servers,
  the endpoint is `s-<id>.server.transfer.<region>.amazonaws.com`.
  For VPC servers, you control DNS — typically a Route 53 private
  hosted zone record pointing at the server's VPC endpoint.

- **Pre-signed URLs for file operations.** Transfer Family uses
  pre-signed S3 URLs internally for uploads/downloads — the IAM role
  must have `s3:GetObject` and `s3:PutObject` for the URL generation
  to succeed, even when the session policy scopes the path.

## Recent AWS features (2024-2026)

- **Transfer Family AS2 (2023-2024 GA):** app-level B2B file exchange
  over HTTP/HTTPS, RFC 4130 compliant. Local and partner profiles with
  cert-based mutual auth. Asynchronous MDN by default. Replaces the
  need for a third-party AS2 gateway for many B2B integrations.
- **Managed workflows (2024-2025):** native step-based workflow engine
  triggered `OnUpload` or `OnPartialUpload`. Step types: COPY, DELETE,
  TAG, CUSTOM (Lambda). Exception steps run on failure. Replaces the
  common pattern of EventBridge + Lambda for inbound file processing.
- **VPC_ENDPOINT endpoint type (2024-2025):** attaches the server to
  your VPC without provisioning a per-subnet ENI. Single endpoint
  serves all AZs. Preferred over the older VPC type for multi-AZ
  resilience.
- **Structured CloudWatch logging (2024):** JSON-formatted logs with
  user, file, operation, and timestamp fields. Replaces the older
  text-format logs. Queryable via CloudWatch Logs Insights.
- **EFS storage backend (2024-2025):** EFS-backed home directories for
  users requiring POSIX file system semantics. Optional EFS access
  points for chroot-like isolation. S3 remains the most common
  backend.
- **Directory Service Simple AD deprecation (2025):** Simple AD no
  longer supported for new Transfer Family servers. Use Managed
  Microsoft AD only.
- **Tag-based access control (2024-2025):** ABAC via resource tags
  on the server and user — useful for multi-tenant Transfer Family
  deployments.
- **Per-server throttling and queueing (2024-2025):** server-side
  queueing of concurrent connections beyond the per-server limit,
  removing silent connection drops under load.
