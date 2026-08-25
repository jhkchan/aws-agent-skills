# Advanced Patterns (load on demand) — Config Aggregator Deployer

2024-2026 feature changes and edge-case handling, moved verbatim from SKILL.md.


---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Proactive rules GA (2024-2025):** Config rules can now
  evaluate resources BEFORE they are created via
  `StartResourceEvaluation`. CloudFormation, CDK, and Terraform
  integrate with proactive rules to block non-compliant resources
  at deployment time. Managed rules support proactive mode by
  setting `Proactive: true`.

- **Config aggregator with Lambda processor (2024-2025):**
  Organization config rules can now use Lambda functions as
  evaluation engines, enabling custom compliance logic across all
  accounts. Integrates with CloudTrail event matching for
  near-real-time evaluation.

- **Conformance pack org-level improvements (2024):**
  `PutOrganizationConformancePack` now supports inline template
  body (not just S3 URI), enabling IaC-native deployment.
  Per-account status via `GetOrganizationConformancePackDetailedStatus`.

- **Config multi-account aggregation throughput (2025):**
  Increased source accounts per organization aggregator from
  3,000 to 10,000, supporting larger enterprise deployments.

- **Resource evaluation SDK expansion (2025):** proactive
  evaluation now supports 50+ resource types including all EC2,
  S3, IAM, and RDS resources, with expanded managed rule coverage.

- **Config rules for new services (2024-2025):** new managed rules
  for AWS Backup, Systems Manager, and AWS WAF, enabling
  compliance checks in conformance packs.

## Edge-case handling (moved from SKILL.md)

- **Aggregator shows no source accounts.** For org aggregators:
  verify Config is a trusted service in Organizations and the
  delegated admin is registered. For authorized-account
  aggregators: verify `PutAggregationAuthorization` was called on
  each source account with the correct aggregator account ID and
  region.

- **Source account status shows FAILED.** The source account's
  Config recorder may be stopped, delivery channel missing, or
  ConfigRole lacking permissions. Check
  `describe-configuration-recorder-status` on the source account.
  For authorized accounts, verify the aggregation authorization
  region matches the aggregator region.

- **Conformance pack fails on some accounts.** Check
  `GetOrganizationConformancePackDetailedStatus` for per-account
  errors. Common causes: IAM role missing in member, S3 bucket
  policy blocking Config, or template syntax error for region-
  specific resource types.

- **Lambda processor rule never evaluates.** Verify the Lambda
  resource policy grants `lambda:InvokeFunction` to
  `config.amazonaws.com`. Check CloudWatch Logs for execution
  errors.

- **Proactive evaluation returns NOT_APPLICABLE.** The resource
  type may not be supported for proactive evaluation, or the rule
  may not have `Proactive: true` set. Verify the rule's
  `Proactive` flag and resource type support.

- **Aggregator exceeds account limit.** Organization aggregators
  support up to 10,000 source accounts (2025 limit). For larger
  fleets, use multiple aggregators partitioned by OU or region.
