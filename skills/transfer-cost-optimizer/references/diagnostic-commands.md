# Diagnostic Commands — Transfer Family Cost Optimizer

Pre-flight data, verification, and safety listings moved verbatim from SKILL.md. Loaded on demand.

## Pre-flight data gate — required data sources

**Required data sources** (summarized — see reference for full CLI):
1. Server configuration: `aws transfer describe-server --server-id <id>`
2. ConcurrentSessions, FilesIn, FilesOut (14-30 day window): `aws cloudwatch get-metric-statistics --namespace AWS/Transfer`
3. User list and activity: `aws transfer list-users --server-id <id>` + `describe-user`
4. Managed workflows: `aws transfer list-workflows` + `describe-workflow`
5. CloudWatch Logs volume: `aws logs describe-metric-filters` + `get-metric-statistics` on `IncomingLogEvents`
6. Cost Explorer Transfer spend: `aws ce get-cost-and-usage --filter '{"Dimensions":{"Key":"SERVICE","Values":["Transfer"]}}'`
7. Custom IdP Lambda (if API_GATEWAY): `aws lambda get-function-configuration` + CloudWatch invocations
8. Step Functions executions (if managed workflow): `aws stepfunctions get-execution-history`

## Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `describe-server` returns `ResourceNotFoundException` | Server does not exist in this region. Skip. |
| `ConcurrentSessions` metric absent (server never used) | **NEED_MORE_INFO**. Verify server wiring; may be idle since creation. |
| Cost Explorer Transfer line items absent | **NEED_MORE_INFO**. Transfer Family may not be in use, or filter is wrong. |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `State = OFFLINE` | Server is stopped. Surface as already-idle; no per-hour charge while offline. |
| CloudWatch `IncomingBytes` for Transfer log group absent | Logging may be disabled or log group deleted. Surface gap. |
| IAM denies `transfer:DescribeServer` | Surface as BLOCKED; cannot evaluate without server config. |

When Cost Explorer and CloudWatch metrics disagree, CloudWatch
(`ConcurrentSessions`, `FilesIn`, `FilesOut`) is the ground truth for
usage patterns — Cost Explorer reflects invoiced spend which may lag.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Verify client connectivity before PUBLIC migration.** Confirm all
  clients can reach the server over the public internet before
  migrating from VPC/VPC_ENDPOINT.
- **Preserve user configurations during server migration.** When
  creating a new server and migrating users, copy all SSH public keys,
  home directory mappings, and session policies before deleting the old
  server.
- **Test the simplified workflow before cutover.** Run the new workflow
  on a test file to verify all required transformations still execute
  correctly.
- **Server deletion is irreversible.** `delete-server` removes the
  server and all its configuration. Ensure user data (home directories
  in S3) is preserved before deletion.
- **Log level changes apply to new transfers only.** In-flight log
  events are not re-filtered.
- **Concurrency limit changes are immediate.** Reducing the limit may
  reject in-flight sessions if the current count exceeds the new limit.
- **Bulk-operation limit:** Process at most 5 servers per batch. Sort
  by estimated savings, verify each batch before proceeding. Abort if
  any server shows increased errors or session rejection post-change.
