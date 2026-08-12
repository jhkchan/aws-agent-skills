# Eval prompt: custom-idp-and-session-optimization

Optimise the following AWS Transfer Family server for cost. Walk the
custom-identity-provider (Lambda per-auth) and session-duration
decision frameworks and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

ServerId: s-custom-idp-and-session-optimization
EndpointType: PUBLIC
Protocols: [SFTP]
Region: us-east-1
IdentityProviderType: API_GATEWAY (custom Lambda IdP)
Concurrency: 15 (configured), observed avg 4, p99 8
Users: 40 active

Custom IdP Lambda:
  - Function: transfer-idp-auth
  - Invocations: 80,000/month (one per session start)
  - Average duration: 250 ms
  - No auth caching configured
  - Cold starts: 15% of invocations
  - API Gateway requests: 80,000/month

Managed workflow: NONE

Metrics (last 30 days):
  - ConcurrentSessions: avg 4, p95 8, p99 8
  - FilesIn: 40,000/month
  - FilesOut: 10,000/month
  - BytesIn: 30 GB/month
  - BytesOut: 10 GB/month
  - UserSessionsStarted: 80,000/month
  - Average session duration: 45 minutes
  - Average files per session: 0.6 (most sessions transfer < 1 file)

CloudWatch Logs volume: 30 GB/month
Cost Explorer (Service=Transfer, last 30 days): $312.00

Workload context: partner portal with custom authentication via
API Gateway + Lambda. High session-start rate (80,000/month) but
low file-transfer rate (0.6 files per session). Most sessions are
partners connecting, checking for files, and disconnecting
without transferring. Auth caching is not configured — every
session start triggers a fresh Lambda invocation.
