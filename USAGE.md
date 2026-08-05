# USAGE — AWS CloudOps Agent Skills

Detailed per-skill invocation guide plus a full end-to-end CloudOps-audit
pipeline walkthrough. For install instructions, see the
[README](README.md). For slash-command reference, see the table below.

---

## Slash Command Quick Reference

| Command | Phase | What it does |
|---|---|---|
| `/aws:pipeline` | All | Start or resume the full CloudOps pipeline from the orchestrator |
| `/aws:status` | — | Emit `[Phase: X | Resources: Y | Skills routed: Z]` one-liner |
| `/aws:help` | — | List all commands + natural-language triggers + skill inventory |
| `/aws:audit-s3-public-access` | 2 Audit | Audit S3 bucket configs for public exposure — emits VERDICT per bucket |
| `/aws:audit-iam-least-privilege` | 2 Audit | Classify an IAM policy document for wildcard/escalation risk (routes to `iam-least-privilege-advisor`) |
| `/aws:audit-ec2-security-groups` | 2 Audit | Audit EC2 security groups for exposed ports and compliance violations |
| `/aws:audit-wafv2-web-acl` | 2 Audit | Audit WAFv2 Web ACLs for default-action posture, managed-rule coverage, COUNT-mode paralysis, shadow rules, and logging gaps |
| `/aws:triage-accessanalyzer-findings` | 2 Audit | Triage IAM Access Analyzer findings (external access + unused access) into risk verdicts — emits VERDICT per finding |
| `/aws:audit-secretsmanager-rotation` | 2 Audit | Audit Secrets Manager secrets for rotation health, Lambda wiring, staleness, and recovery-window state |
| `/aws:triage-guardduty-findings` | 3 Prioritize | Triage GuardDuty findings into context-aware severity (CRITICAL/HIGH/MEDIUM/LOW/LIKELY_FALSE_POSITIVE) with false-positive detection |
| `/aws:audit-kms-key-policy` | 2 Audit | Audit KMS key policies for cross-account decrypt, wildcard kms:*, rotation gaps, deletion-window exposure (routes to `kms-key-policy-auditor`) |
| `/aws:audit-sts-cross-account-role` | 2 Audit | Audit IAM role trust policies for cross-account/external trust, wildcard Principal, and confused-deputy risk (routes to `sts-cross-account-role-auditor`) |
| `/aws:audit-inspector2-coverage-findings` | 2 Audit | Audit Inspector2 coverage gaps + finding severity — CRITICAL/HIGH/MEDIUM/LOW/COVERED per resource (routes to `inspector2-coverage-finding-auditor`) |
| `/aws:audit-cognito-user-pool` | 2 Audit | Audit Cognito user pools for MFA, password policy, auth-flow safety, OAuth exposure, ASF mode — emits INSECURE/WEAK/ADEQUATE/OK per pool (routes to `cognito-idp-user-pool-auditor`) |
| `/aws:audit-acm-certificate-expiry` | 2 Audit | Audit ACM certificates for expiry, renewal status, and key-algorithm compliance — emits VERDICT per certificate (routes to `acm-certificate-expiry-auditor`) |
| `/aws:audit-securityhub-control-compliance` | 2 Audit | Audit Security Hub control findings — classifies lifecycle states (suppressed, resolved, archived, NOT_AVAILABLE) into FAILED/WARNING/PASSED/NOT_APPLICABLE + maps to fix action (routes to `securityhub-control-compliance-auditor`) |
| `/aws:audit-ecs-task-definition` | 2 Audit | Audit ECS task definitions for privileged containers, plaintext secrets in env vars, host network mode, root-user execution, missing resource limits — emits PRIVILEGED/SECRET_LEAK/INSECURE/CONFIG_GAP/OK per task (routes to `ecs-task-definition-auditor`) |
| `/aws:audit-backup-plan` | 2 Audit | Audit AWS Backup plans for coverage gaps, vault risks (no lock, governance-mode lock, AWS-managed key), impossible lifecycle configs, and compliance violations — emits COVERAGE_GAP/VAULT_RISK/NONCOMPLIANT/CONFIG_GAP/OK per plan (routes to `backup-plan-auditor`) |
| `/aws:audit-eks-cluster` | 2 Audit | Audit EKS clusters for public API endpoint, disabled control-plane logging, IAM auth mapRoles, security group exposure, and outdated version (routes to `eks-cluster-auditor`) |
| `/aws:audit-compute-optimizer-findings` | 2 Audit | Audit Compute Optimizer findings for EC2/EBS/Lambda/ASG — confidence-gated UNDERUTILIZED/NOT_OPTIMIZED/OK with per-finding risk + CLI remediation (routes to `compute-optimizer-findings-auditor`) |
| `/aws:audit-lambda-runtime-deprecation` | 2 Audit | Audit Lambda functions for deprecated/EOL runtimes, over-permissioned execution roles, public function URL exposure, and observability config gaps — emits VERDICT per function (routes to `lambda-runtime-deprecation-auditor`) |
| `/aws:audit-autoscaling-group` | 2 Audit | Audit Auto Scaling Groups for launch-template health, ELB health-check integrity, mixed-instances Spot diversification, capacity bounds, and unhealthy-termination behavior — emits MISCONFIGURED/CONFIG_GAP/OK per ASG (routes to `autoscaling-group-auditor`) |
| `/aws:audit-ecr-repository` | 2 Audit | Audit ECR private repositories for public access, scan-on-push gaps, lifecycle-policy absence, tag-immutability gaps, unscanned images — emits PUBLIC/NO_SCAN/NO_LIFECYCLE/CONFIG_GAP/OK per repo (routes to `ecr-repository-auditor`) |
| `/aws:audit-efs-filesystem` | 2 Audit | Audit EFS filesystems for encryption-at-rest, public filesystem policy, TLS enforcement, lifecycle management, and access point governance — emits UNENCRYPTED/PUBLIC_POLICY/CONFIG_GAP/OK per filesystem (routes to `efs-filesystem-auditor`) |
| `/aws:audit-dlm-lifecycle-policy` | 2 Audit | Audit DLM EBS snapshot lifecycle policies for disabled state, empty tag/resource targets, invalid schedules, weak retention, missing cross-region copy (DR gap), CopyTags metadata loss, and per-volume snapshot quota risk — emits NO_POLICY/MISCONFIGURED/CONFIG_GAP/OK per policy (routes to `dlm-lifecycle-policy-auditor`) |
| `/aws:audit-ebs-volume` | 2 Audit | Audit EBS volumes and snapshots for unencrypted state, unattached cost waste, legacy gp2/io1/standard volume types (gp3/io2 upgrade), stale snapshots (with FSR cost-dominance check), and public-snapshot block-data exposure — emits UNENCRYPTED/UNATTACHED/LEGACY_TYPE/STALE_SNAPSHOT/PUBLIC_SNAPSHOT/OK per resource (routes to `ebs-volume-auditor`) |
| `/aws:audit-budgets` | 2 Audit | Audit AWS Budgets for cost-overrun blind spots — zero budgets, decorative budgets (no notifications), SNS topic policies that silently block delivery (missing budgets.amazonaws.com publish), single-threshold/no-forecast alerts, breached or on-track-to-breach spend, and missing zero-spend guardrails for new accounts — emits NO_BUDGET/NO_ALERT/CONFIG_GAP/OK per account (routes to `budgets-auditor`) |
| `/aws:audit-route53-records` | 2 Audit | Audit Route 53 records for missing health checks on weighted/failover/latency routing, dangling ALIAS targets, DNSSEC gaps, public-zone private-IP exposure, TTL inconsistency — emits NO_HEALTH_CHECK/DNSSEC_GAP/DANGLING/CONFIG_GAP/OK per record (routes to `route53-record-auditor`) |
| `/aws:audit-auditmanager-assessment` | 2 Audit | Audit Audit Manager assessments for evidence-collection integrity (stopped/INACTIVE, Config/CloudTrail data-source breaks, NOT_ASSESSED burden), compliance rate, delegation wiring, and settings posture (KMS/SNS/reports-destination/process-owners) — emits INCOMPLETE_EVIDENCE/LOW_COMPLIANCE/CONFIG_GAP/OK per assessment (routes to `auditmanager-assessment-auditor`) |
| `/aws:audit-cur-cost-usage-report` | 2 Audit | Audit Cost and Usage Report (CUR) for coverage, staleness, report version, Athena integration, S3 versioning, and time-horizon health — emits NO_CUR/STALE/CONFIG_GAP/OK per report (routes to `cur-cost-usage-report-auditor`) |
| `/aws:audit-cost-optimization-hub` | 2 Audit | Audit Cost Optimization Hub for recommendation enablement, member-account coverage, effort-level distribution, and stale high-value unactioned recommendations — emits DISABLED/NO_MEMBER_ACCOUNTS/HIGH_EFFORT/CONFIG_GAP/OK per account (routes to `cost-optimization-hub-recommendations-auditor`) |
| `/aws:audit-billing-account` | 2 Audit | Audit AWS account billing posture — root MFA and access keys, IAM user/group billing access delegation, Cost Anomaly Detection enablement, billing budgets, and free-tier usage alerts — emits ROOT_BILLING/NO_ANOMALY_DETECTION/CONFIG_GAP/OK per account (routes to `billing-account-auditor`) |
| `/aws:audit-ce-cost-anomaly` | 2 Audit | Audit Cost Explorer anomaly-detection subscriptions (monitor type, subscription frequency, threshold calibration), RI/SP commitment coverage gaps on steady-state compute, idle-resource detection readiness (CUR resource-ID gating), and report-subscription cadence (IMMEDIATE vs WEEKLY mismatch) — emits NO_ANOMALY_SUB/LOW_RI_COVERAGE/CONFIG_GAP/OK per account (routes to `ce-cost-anomaly-auditor`) |
| `/aws:audit-elbv2-load-balancer` | 2 Audit | Audit ALB/NLB for insecure TLS listener policies (TLS 1.0/1.1, weak ciphers), disabled access logs, permissive security groups, idle load balancers (no targets), disabled cross-zone (NLB), and missing deletion protection — emits INSECURE_LISTENER/NO_ACCESS_LOGS/PERMISSIVE_SG/IDLE/CONFIG_GAP/OK per LB (routes to `elbv2-load-balancer-auditor`) |
| `/aws:audit-networkmanager-core-network` | 2 Audit | Audit Network Manager (Cloud WAN) core networks for detached attachments, permissive resource/segment policies, CIDR overlap, and LATEST-vs-LIVE policy mismatch — emits DETACHED_ATTACHMENT/PERMISSIVE_POLICY/CIDR_OVERLAP/CONFIG_GAP/OK per core network (routes to `networkmanager-core-network-auditor`) |
| `/aws:audit-directconnect-topology` | 2 Audit | Audit Direct Connect topology for single-path failure risk (same-POP pseudo-diversity), MACSec `should_encrypt`/`no_encrypt` on capable hardware, public-VIF BGP MD5 (route-hijack defence), VIF redundancy via DXGW, and LOA-CFA provisioning state — emits SINGLE_CONNECTION/NO_ENCRYPTION/CONFIG_GAP/OK per topology (routes to `directconnect-auditor`) |
| `/aws:audit-cloudtrail-org-trail` | 2 Audit | Audit CloudTrail organization trails for org coverage, multi-region logging, KMS encryption (SSE-KMS), log-file validation (digest integrity), CloudWatch Logs delivery, CloudTrail Insights enablement, and log retention — emits NO_ORG_TRAIL/NO_ENCRYPTION/NO_VALIDATION/NO_INSIGHTS/CONFIG_GAP/OK per trail (routes to `cloudtrail-org-trail-auditor`) |
| `/aws:audit-cloudwatch-logs-retention` | 2 Audit | Audit CloudWatch Logs log groups for Never-expire retention (silent infinite-cost accumulation), missing SSE-KMS customer-managed-key (CMK) encryption, retention × volume cost risk, subscription filter fan-out (Lambda/Kinesis/cross-account destination), missing metric filters, and absent CloudWatch Logs Anomaly Detectors — emits NO_RETENTION/NO_ENCRYPTION/COST_RISK/CONFIG_GAP/OK per log group (routes to `cloudwatch-logs-retention-auditor`) |
| `/aws:audit-dynamodb-table` | 2 Audit | Audit DynamoDB tables for encryption (KMS), PITR, capacity mode (on-demand vs provisioned w/ autoscaling), TTL, backup, GSI/LSI quota risk, and deletion protection — emits UNENCRYPTED/NO_PITR/CAPACITY_MISMATCH/CONFIG_GAP/OK per table (routes to `dynamodb-table-auditor`) |
| `/aws:audit-config-recorder-coverage` | 2 Audit | Audit AWS Config recorder coverage (allSupported, includeGlobalResourceTypes), delivery channel health (FAILURE status, NO_SUCH_BUCKET, ACCESS_DENIED), Config rules deployment, and conformance packs (deployment status) — emits INCOMPLETE_COVERAGE/NO_RULES/DELIVERY_GAP/CONFIG_GAP/OK per region (routes to `config-recorder-coverage-auditor`) |
| `/aws:audit-trustedadvisor-checks` | 2 Audit | Audit Trusted Advisor check results for security, fault-tolerance, cost-optimization, performance, and service-limits findings — including support-tier gating (Basic/Developer = 7 of ~115 checks), stale results (>24h), excluded-resource blind spots, and `not_available` statuses — emits CRITICAL_CHECK/WARNING_CHECK/CONFIG_GAP/OK per check (routes to `trustedadvisor-check-auditor`) |
| `/aws:audit-rds-instance` | 2 Audit | Audit RDS DB instances for public accessibility (internet-exposed database), encryption-at-rest (immutable post-creation), deletion protection, Multi-AZ availability, automated backups / PITR, auto minor-version upgrade, and Enhanced Monitoring — emits PUBLIC/UNENCRYPTED/NO_DELETION_PROTECTION/SINGLE_AZ/CONFIG_GAP/OK per instance (routes to `rds-instance-auditor`) |
| `/aws:audit-redshift-cluster` | 2 Audit | Audit Amazon Redshift provisioned clusters for public accessibility (internet-exposed petabyte-scale data warehouse), KMS encryption-at-rest (immutable post-creation), require_ssl parameter-group enforcement, S3 audit logging (CloudTrail covers control-plane only — not SQL), automated-snapshot retention (PITR), enhanced VPC routing (COPY/UNLOAD data-path privacy), and VPC security-group ingress on the cluster port — emits PUBLIC/NO_ENCRYPTION/NO_SSL/NO_AUDIT_LOG/CONFIG_GAP/OK per cluster (routes to `redshift-cluster-auditor`) |
| `/aws:audit-opensearch-domain` | 2 Audit | Audit Amazon OpenSearch Service (provisioned, not Serverless) domains for encryption-at-rest (KMS CMK vs AWS-managed aws/es), node-to-node encryption, fine-grained access control (FGAC / Advanced Security), public access via resource-policy Principal `*` with `es:ESHttp*` data-plane grants, dedicated master node type/count (t2/t3.small.search below AWS recommendation, single master = no HA quorum), and slow-log publishing to CloudWatch Logs — emits NO_ENCRYPTION/PUBLIC_ACCESS/NO_FGAC/CONFIG_GAP/OK per domain (routes to `opensearch-domain-auditor`) |
| `/aws:audit-controltower-controls` | 2 Audit | Audit Control Tower landing-zone state, enabled controls (preventive/detective/proactive), SCP drift, guardrail enforcement integrity, Config recorder gaps, and account-factory baseline health — emits DRIFT/DISABLED_CONTROL/CONFIG_GAP/OK per OU or landing zone (routes to `controltower-control-auditor`) |
| `/aws:audit-wellarchitected-workload` | 2 Audit | Audit Well-Architected Tool workloads for review staleness (effectiveReviewDate > 180 days), per-pillar high-risk issue counts (security zero-tolerance + aggregate > 5), milestone tracking gaps, UNANSWERED majority, and remediation plan completeness — emits STALE_REVIEW/HIGH_RISK/CONFIG_GAP/OK per workload (routes to `wellarchitected-workload-auditor`) |
| `/aws:audit-organizations-scp` | 2 Audit | Audit Organizations SCPs for effective permissions across the OU hierarchy — FullAWSAccess inheritance, deny-list guardrails (LeaveOrganization, security-service disruption, region restriction), account-level overrides, silently ineffective condition keys — emits PERMISSIVE_SCP/MISSING_GUARDRAIL/CONFIG_GAP/OK per target (routes to `organizations-scp-auditor`) |
| `/aws:audit-codecommit-repository` | 2 Audit | Audit CodeCommit repositories for approval-rule-template coverage, customer-managed KMS encryption, default-branch deletion protection (IAM enforced, not native), notification-rule alerting, and the CodeCommit service-wide deprecation/maintenance risk — emits NO_APPROVAL_RULE/NO_ENCRYPTION/CONFIG_GAP/DEPRECATION_RISK/OK per repository (routes to `codecommit-repository-auditor`) |
| `/aws:audit-codebuild-project` | 2 Audit | Audit CodeBuild projects for privileged mode (Docker-in-Docker host access without Docker justification), plaintext secrets in environmentVariables, unencrypted S3 logs and build artifacts (encryptionDisabled=true / no kmsKeyArn), over-permissive service-role blast radius (admin wildcard, PassRole on `*`, unscoped `codebuild.amazonaws.com` trust policy), VPC config (missing or public-subnet isolation), and public build-status badge leakage — emits PRIVILEGED/SECRET_LEAK/NO_ENCRYPTION/OVERPERMISSIVE_ROLE/CONFIG_GAP/OK per project (routes to `codebuild-project-auditor`) |
| `/aws:audit-apigateway-resource-policy` | 2 Audit | Audit API Gateway REST/HTTP APIs for unauthenticated public methods (authorizationType NONE), API-key-as-auth misuse, cross-account resource policy grants, missing usage plans and rate limiting, and absent WAF Web ACL associations — emits PUBLIC_NO_AUTH/NO_RATE_LIMIT/CONFIG_GAP/OK per API (routes to `apigateway-resource-policy-auditor`) |
| `/aws:audit-codedeploy-deployment-group` | 2 Audit | Audit CodeDeploy deployment groups for auto-rollback enablement (DEPLOYMENT_FAILURE trigger), CloudWatch alarm monitoring (enabled + populated, ignorePollAlarmFailure), deployment-config risk (AllAtATime, zero minimum-healthy-hosts), and blue/green termination posture (immediate termination, no traffic control) — emits NO_ROLLBACK/NO_ALARMS/CONFIG_GAP/OK per deployment group (routes to `codedeploy-deployment-group-auditor`) |
| `/aws:audit-service-quotas-usage` | 2 Audit | Audit AWS Service Quotas for utilization per service, approaching limits (>=80%), CloudWatch alarm coverage on AWS/Usage metrics, applied vs default quota drift, denied/stale quota increase requests, and non-trackable quotas lacking UsageMetric — emits APPROACHING_LIMIT/NO_ALARM/CONFIG_GAP/OK per quota (routes to `service-quotas-usage-auditor`) |
| `/aws:audit-sqs-dlq-policy` | 2 Audit | Audit SQS queues for missing or misconfigured dead-letter queue (DLQ), public access via Principal:* queue policies, encryption-at-rest gaps (SSE-SQS / SSE-KMS), maxReceiveCount tuning, DLQ retention periods, and cross-account DLQ accessibility — emits NO_DLQ/PUBLIC_ACCESS/NO_ENCRYPTION/CONFIG_GAP/OK per queue (routes to `sqs-dlq-policy-auditor`) |
| `/aws:audit-eventbridge-bus-policy` | 2 Audit | Audit EventBridge event buses for public event-injection (Principal:* + PutEvents), missing per-target DLQs, absent customer-managed KMS key, and archive gaps — emits PUBLIC_BUS/NO_DLQ/NO_ENCRYPTION/CONFIG_GAP/OK per bus (routes to `eventbridge-bus-policy-auditor`) |
| `/aws:audit-sns-topic-public-subscription` | 2 Audit | Audit SNS topics for public subscription exposure (Principal:* with sns:Subscribe/Publish in topic policy), missing KMS encryption, delivery-status logging gaps, FIFO deduplication misconfiguration, and cross-account subscriptions — emits PUBLIC_SUBSCRIPTION/NO_ENCRYPTION/CONFIG_GAP/OK per topic (routes to `sns-topic-public-subscription-auditor`) |
| `/aws:audit-codepipeline-pipeline` | 2 Audit | Audit CodePipeline pipelines for artifact-store encryption (KMS CMK), cross-account deploy roles, disabled stage transitions, deprecated source credentials (GitHub v1 OAuth), and manual-approval gate coverage — emits NO_ENCRYPTION/OVERPERMISSIVE_ROLE/DISABLED_STAGE/CONFIG_GAP/OK per pipeline (routes to `codepipeline-pipeline-auditor`) |
| `/aws:audit-stepfunctions-statemachine` | 2 Audit | Audit Step Functions state machines for execution logging coverage (level ALL + includeExecutionData), X-Ray tracing enablement (including the Express-workflow no-op trap), execution-role blast radius (wildcard actions, states:StartExecution chaining, iam:PassRole), and ASL definition validation (missing Catch/Retry on fallible Tasks, missing TimeoutSeconds, unreachable states, cyclic references without exit) — emits NO_LOGGING/NO_TRACING/OVERPERMISSIVE_ROLE/CONFIG_GAP/OK per state machine (routes to `stepfunctions-statemachine-auditor`) |
| `/aws:audit-health-event` | 2 Audit | Audit AWS Health for open issue events with IMPAIRED affected entities, upcoming scheduled changes (deadline = startTime), closed-event resolution, Health Organizational View enablement (healthServiceAccessStatusForOrganization), and EventBridge `aws.health` rule wiring on the default bus — emits UNRESOLVED_EVENT/SCHEDULED_CHANGE/CONFIG_GAP/OK per event or account/org scope (routes to `health-event-auditor`) |
| `/aws:audit-sagemaker-endpoint` | 2 Audit | Audit SageMaker endpoints for encryption (KMS at rest + inter-container traffic on inference pipelines), execution-role blast radius (wildcard actions, sagemaker:*, iam:PassRole), VPC configuration (VpcConfig-on-Model knowledge delta — internet-facing vs private), data capture + model monitoring schedule coverage, and instance count for high availability — emits NO_ENCRYPTION/OVERPERMISSIVE_ROLE/NO_MONITORING/PUBLIC_ENDPOINT/CONFIG_GAP/OK per endpoint (routes to `sagemaker-endpoint-auditor`) |
| `/aws:audit-ssm-managed-instance` | 2 Audit | Audit SSM managed instances for coverage (SSM Agent reachable + IAM profile attached), association compliance, patch baseline adherence, Session Manager vs SSH exposure, inventory collection, and Run Command posture — emits UNMANAGED/NONCOMPLIANT/NO_SESSION_MANAGER/CONFIG_GAP/OK per instance (routes to `ssm-managed-instance-auditor`) |

| `/aws:audit-dms-replication-task` | 2 Audit | Audit DMS replication tasks for SSL/TLS gaps on source/target endpoints (SslMode none/missing = plaintext), missing CDC/task logging (EnableLogging false — metrics-vs-logs trap), replication instance exposure (PubliclyAccessible, single-AZ CDC position loss), endpoint encryption (KmsKeyId), and task settings integrity (validation, deletion protection) — emits NO_TLS/NO_LOGGING/CONFIG_GAP/OK per task (routes to `dms-replication-task-auditor`) |
| `/aws:audit-bedrock-model-access` | 2 Audit | Audit Amazon Bedrock model access posture — invocation logging coverage (S3/CloudWatch/DataFirehose + per-modality delivery flags), customer-managed KMS encryption vs AWS-managed default, Anthropic Claude geo-block risk in APAC jurisdictions (models list as enabled but fail at invocation with ValidationException), provisioned throughput commitment state, and guardrail coverage on enabled models — emits NO_LOGGING/NO_ENCRYPTION/GEO_BLOCK_RISK/CONFIG_GAP/OK per inventory (routes to `bedrock-model-access-inventory`) |
| `/aws:audit-cloudwatch-alarm` | 2 Audit | Audit CloudWatch alarms for missing alarm actions (SNS/Lambda/AutoScaling), insufficient-data handling (TreatMissingData defaults to "missing" — not "notBreaching"), anomaly-detection coverage vs static thresholds on high-variance metrics, composite alarm integrity (Rule expression, child alarm references, escalation actions), structural config errors (DatapointsToAlarm > EvaluationPeriods), and alarm state history — emits NO_ANOMALY/NO_ACTION/INSUFFICIENT_DATA/CONFIG_GAP/OK per alarm (routes to `cloudwatch-alarm-auditor`) |
| `/aws:audit-bedrock-guardrail-coverage` | 2 Audit | Audit Bedrock Guardrails for model coverage gaps (guardrails are per-request, not per-model), DRAFT-vs-READY enforcement status (DRAFT = zero enforcement), content-filter strength (hate/insult/sexual/violence outputStrength NONE), contextual grounding threshold (0.0 = silently disabled), denied topics, word filters, and per-application bypass risk — emits NO_GUARDRAIL/INCOMPLETE_COVERAGE/WEAK_FILTER/CONFIG_GAP/OK per guardrail or deployment (routes to `bedrock-guardrail-coverage-auditor`) |
| `/aws:audit-resiliencehub-app-assessment` | 2 Audit | Audit Resilience Hub app assessments for assessment staleness (>90 days), resiliency policy binding and tier-to-RTO/RPO calibration, per-tier compliance breaches (MissionCritical/Critical NonCompliant triggers HIGH_RISK), aggregate compliance score (<80 = LOW_COMPLIANCE), app-version drift, failed/pending assessment status (no data = CONFIG_GAP not zero compliance), and unimplemented alarm/SDD/test recommendations — emits STALE_ASSESSMENT/HIGH_RISK/LOW_COMPLIANCE/CONFIG_GAP/OK per app (routes to `resiliencehub-app-assessment-auditor`) |
| `/aws:audit-kinesis-stream` | 2 Audit | Audit Kinesis Data Streams for encryption-at-rest gaps (EncryptionType NONE), extended-retention cost exposure (retention > 168h incurs per-GB charges separate from shard-hour fee), shard-count quota-exhaustion risk (approaching 500 default quota), enhanced-monitoring blind spots (missing per-shard IteratorAgeMilliseconds and WriteProvisionedThroughputExceeded), consumer checkpointing posture (classic consumers share 2 MB/s vs enhanced fan-out dedicated), and on-demand vs provisioned mode fit (per-stream-hour floor dominates at low volume) — emits NO_ENCRYPTION/COST_RISK/CONFIG_GAP/OK per stream (routes to `kinesis-stream-auditor`) |
| `/aws:audit-firehose-delivery-stream` | 2 Audit | Audit Kinesis Data Firehose delivery streams for encryption-at-rest gaps (explicit NoEncryption opt-out vs absent EncryptionConfiguration relying on bucket default SSE-S3 vs SSE-KMS CMK), BufferingHints quota violations (SizeInMBs 1-128, IntervalInSeconds 60-900), Lambda transformation backup posture (S3BackupMode Disabled = silent corruption vector), CloudWatch error-logging silence (LoggingConfig.Enabled false = transformation failures invisible), source-backup absence under dynamic partitioning (silent data-loss on JQ extraction failure), and dynamic-partitioning structural integrity (MetadataExtraction wiring, ExtendedS3 requirement, RetryDuration=0 immediate-fail trap) — emits NO_ENCRYPTION/CONFIG_GAP/OK per delivery stream (routes to `firehose-delivery-stream-auditor`) |
| `/aws:audit-msk-cluster` | 2 Audit | Audit Amazon MSK (Managed Kafka) clusters for encryption in-transit (ClientBroker PLAINTEXT/TLS_PLAINTEXT = NO_ENCRYPTION — plaintext path breaks guarantee), client authentication (unauthenticated enabled = open data plane), public access (SERVICE_PROVIDED_EIPS = internet-reachable brokers), broker logging (all destinations disabled), and encryption at-rest KMS key governance (AWS-managed vs customer-managed CMK) — emits NO_ENCRYPTION/UNAUTHENTICATED/PUBLIC_ACCESS/CONFIG_GAP/OK per cluster (routes to `msk-cluster-auditor`) |

| `/aws:audit-emr-cluster` | 2 Audit | Audit EMR clusters for encryption gaps (S3, local-disk, in-transit), over-permissive IAM roles, Kerberos auth, block public access, debug logging — emits NO_ENCRYPTION/OVERPERMISSIVE_ROLE/CONFIG_GAP/OK per cluster (routes to `emr-cluster-auditor`) |
| `/aws:audit-glue-crawler-job` | 2 Audit | Audit Glue crawlers/jobs for data-catalog encryption (EncryptionAtRest / ConnectionPasswordEncryption), JDBC connection SSL (JDBC_ENFORCE_SSL), IAM execution-role blast radius (glue:* / s3:* / iam:PassRole on star — glue:CreateJob pass-role vector), SecurityConfiguration coverage (CloudWatch logs / S3 spills / bookmarks), job-bookmark encryption, EOL Glue version (0.9/1.0), and S3 source bucket encryption (independent of catalog) — emits NO_ENCRYPTION/OVERPERMISSIVE_ROLE/CONFIG_GAP/OK per resource (routes to `glue-crawler-job-auditor`) |
| `/aws:audit-cleanrooms-collaboration` | 2 Audit | Audit AWS Clean Rooms collaborations for membership-status gaps (INVITED/REMOVED/LEFT members — perspective-relative status), privacy-budget risks (differential privacy disabled at collaboration level vs additionalAnalyses=0 per-query enforcement gap, epsilon near-exhaustion >=80% of per-member cap with no reset, aggregate constraints absent = no structural privacy floor), analysis-template SQL-validation defects (dangling configured-table aliases, unresolved ${param} tokens, columns outside allowedColumns), protected-query output S3 widening, and configured-audience activation gaps (cleanroomsml model in CREATE_FAILED/CREATE_IN_PROGRESS, missing destinationConfig) — emits MEMBERSHIP_GAP/PRIVACY_RISK/CONFIG_GAP/OK per collaboration (routes to `cleanrooms-collaboration-auditor`) |
| `/aws:audit-athena-workgroup` | 2 Audit | Audit Athena workgroups for query-result encryption (SSE-S3/SSE-KMS on ResultConfiguration), BytesScannedCutoffPerQuery data-scan limit, EnforceWorkGroupConfiguration enforcement posture (false = encryption/OutputLocation advisory; only the DSL is binding), query-history retention via CloudTrail Athena data events (GetQueryExecution has a fixed 45-day window), and named-query IAM exposure (Principal:* + athena:GetNamedQuery = SQL exfiltration) — emits NO_ENCRYPTION/NO_LIMITS/CONFIG_GAP/OK per workgroup (routes to `athena-workgroup-auditor`) |
| `/aws:audit-lakeformation-data-lake` | 2 Audit | Audit Lake Formation data lakes for catalog-level super-grants (Permissions ALL on Catalog), cross-account DataLakePrincipalIdentifier principals, ColumnWildcard SELECT without a wired DataCellsFilter, WithGrantablePermissions unbounded delegation chains, grants on tables whose S3 path is not under any registered location, DataLakeAdmins composition (empty / external / over-delegated), and IAMAllowedPrincipals mixed-mode databases — emits OVERPERMISSIVE_GRANT/EXTERNAL_ACCOUNT/CONFIG_GAP/OK per data lake (routes to `lakeformation-data-lake-auditor`) |

Every command has a natural-language equivalent — the orchestrator routes
identically.

## CLI Quick Reference

```bash
# List all discovered skills
node cli/bin/cli.js list

# Route a prompt to the best-matching skill(s)
node cli/bin/cli.js route "check my S3 buckets for public access"

# Validate all skills against the schema
node cli/bin/cli.js validate

# Show skill-suite coverage + eval status
node cli/bin/cli.js status
```

---

## The CloudOps Pipeline (4 phases)

```
Assess         →     Audit          →     Prioritize       →     Remediate
   |                  |                     |                      |
   v                  v                     v                      v
inventory          detective              severity ranking         CLI commands
resource lists     auditors               cost-impact              IaC patches
coverage gaps      deterministic          compliance-mandate       runbook steps
baseline state     VERDICT output         risk-weighted            actionable fixes
```

The orchestrator diagnoses which phase the assessment is in and routes to the
right specialist skill(s). It never duplicates specialist content — always
hands off.

---

## Per-Skill Usage

### 1. aws-orchestrator (entry point)

**Pipeline phase:** Phase 0 — routes all phases.

**What it does:** Diagnoses where the assessment sits in the CloudOps pipeline
(Assess -> Audit -> Prioritize -> Remediate) and routes to the right
specialist skill(s). Emits a phase indicator like
`[Phase: Audit | Skills routed: s3-public-access-auditor]`. Never duplicates
specialist content — always hands off.

**When to invoke (trigger phrases):**

- "check my AWS security posture"
- "audit my whole account"
- "what should I audit first?"
- "help me prioritize these findings"
- "full compliance audit"
- A bare AWS resource name + any audit verb ("audit this bucket", "check this role")

**Example prompt:**

```
You: "I'm onboarding a new AWS account. Audit everything for public
     exposure and give me a prioritized remediation plan."
```

**Expected behavior:**

1. Orchestrator emits phase plan covering all 4 phases.
2. Routes Phase 1 (Assess) -> all skills in discovery mode (inventory).
3. Routes Phase 2 (Audit) -> each specialist for VERDICT.
4. Routes Phase 3 (Prioritize) -> orchestrator ranks findings cross-service.
5. Routes Phase 4 (Remediate) -> each specialist's remediation section.
6. Emits `[Phase: X | Skills routed: Y]` at each transition.

---

### 2. s3-public-access-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-s3-public-access`

**What it does:** Analyzes S3 bucket configurations (Block Public Access
settings, ACLs, and bucket policies) to determine which buckets are publicly
accessible, classify each bucket's exposure level, and provide specific
remediation guidance.

**When to invoke (trigger phrases):**

- "is this S3 bucket public?"
- "check my buckets for public access"
- "BPA settings", "Block Public Access"
- "bucket policy", "ACL", "AllUsers"
- "s3 exposure", "data leak"
- reviewing S3 security before production deployment

**Example prompt:**

```
You: /aws:audit-s3-public-access

     "I have a bucket named 'my-app-uploads' with BPA off and this policy:
     {Effect: Allow, Principal: '*', Action: 's3:GetObject', Resource:
     'arn:aws:s3:::my-app-uploads/*'}. Is it public?"
```

**Expected behavior:**

1. Applies the classification logic in order (BPA -> policy -> ACL -> condition).
2. Emits VERDICT: PUBLIC (Rule 2: unrestricted wildcard Allow).
3. Cites the severity (HIGH — read-only data exfiltration).
4. Provides specific remediation: enable BPA, restrict/remove policy, use CloudFront OAC.

**CLI routing:**

```bash
node cli/bin/cli.js route "check my S3 buckets for public access"
# [Phase: Audit | Skills routed: s3-public-access-auditor]
```

---

### 3. iam-least-privilege-advisor

**Pipeline phase:** Phase 2 — Audit.

**What it does:** Analyzes AWS IAM policies to identify over-permissive
grants — wildcard actions, wildcard resources, privilege-escalation actions
(PassRole, AssumeRole), inverse wildcards (NotAction/NotResource), and
condition-key bypasses — then provides least-privilege remediation.

**Slash command:** `/aws:audit-iam-least-privilege` — or route via `/aws:pipeline`.

**When to invoke (trigger phrases):**

- "is this IAM policy over-permissive?"
- "check for wildcard permissions"
- "privilege escalation risk"
- "PassRole", "AssumeRole"
- "least privilege", "tighten this role"
- "NotAction", "NotResource"
- auditing a role before production deployment

**Example prompt:**

```
You: "Review this role policy: {Action: 'ec2:*', Resource: '*',
     Effect: Allow}. Is it over-permissive?"
```

**Example invocation:**

```bash
# CLI routing (functional orchestrator)
node cli/bin/cli.js route "is this IAM policy over-permissive"
# [Phase: Audit | Skills routed: iam-least-privilege-advisor]
```

**Expected behavior:**

1. Classifies by the wildcard severity matrix.
2. Emits VERDICT: OVERPERMISSIVE (wildcard actions on wildcard resources).
3. Identifies the specific risk: full EC2 access — can modify security groups, key pairs.
4. Provides scoped-down replacement policy with specific actions/resources.

**End-to-end scenario:** see
[`skills/iam-least-privilege-advisor/examples/end-to-end.md`](skills/iam-least-privilege-advisor/examples/end-to-end.md)
for a multi-statement policy walkthrough (tight read grant + PassRole escalation)
covering aggregation, CRITICAL risk escalation, and the `iam:PassedToService`
condition-key remediation.

---

### 4. ec2-security-group-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ec2-security-groups`

**CLI route:**

```bash
node cli/bin/cli.js route "audit my security groups for open ports"
```

**What it does:** Audits EC2 security group inbound rules to identify publicly
exposed ports and provides remediation guidance mapped to CIS AWS Foundations
Benchmark, PCI-DSS, and NIST SP 800-53. Recognizes port ranges, non-TCP
protocols, managed prefix lists, IPv6 sources, and mixed rule sets.

**When to invoke (trigger phrases):**

- "is this security group open?"
- "check for 0.0.0.0/0 rules"
- "port exposure", "open ports"
- "RDP", "SSH", "3389", "22"
- "database port exposed"
- "CIS benchmark", "PCI-DSS controls"
- reviewing an SG before production deployment

**Example prompt:**

```
You: "My security group sg-xxx has an inbound rule: TCP port 22 from
     0.0.0.0/0. Is this a problem?"
```

**Expected behavior:**

1. Classifies the rule: SSH open to the internet.
2. Emits VERDICT: OPEN (Rule: 0.0.0.0/0 on admin port 22).
3. Maps to CIS AWS Foundations Benchmark 4.1 (ensure no security groups allow ingress from 0.0.0.0/0 to port 22).
4. Provides remediation: restrict to known CIDR, use Session Manager instead.

**End-to-end example:** see `skills/ec2-security-group-auditor/example/end-to-end-audit.md`
for a full four-security-group audit walkthrough (ALB, app-tier, database, and
emergency-access SGs) with orchestrator phase transitions.

---

### 5. kms-key-policy-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-kms-key-policy`

**What it does:** Audits KMS key policies and key metadata for cross-account
or external principal access, wildcard `kms:*` grants, the `kms:Decrypt`
blast-radius multiplier, `kms:CreateGrant` delegation vectors, automatic-key-
rotation status, and key-deletion window exposure. Emits a deterministic
severity verdict (CRITICAL | HIGH | MEDIUM | OK) per key with enumerated
findings and specific remediation.

**When to invoke (trigger phrases):**

- "audit this KMS key policy"
- "check for cross-account KMS decrypt"
- "kms wildcard permissions"
- "is key rotation enabled?"
- "key pending deletion"
- "kms:CreateGrant delegation"
- "kms blast radius"
- reviewing a KMS key before production deployment

**Example prompt:**

```
You: "This KMS key grants kms:Decrypt to arn:aws:iam::222222222222:role/external
     with no condition. Rotation is off. What's the risk?"
```

**Expected behavior:**

1. Classifies the principal scope (cross-account), action danger
   (DATA_ACCESS — Decrypt is a blast-radius multiplier), and condition
   strength (none).
2. Emits VERDICT: CRITICAL (Rule 5c — cross-account decrypt, no condition).
3. Identifies the rotation gap as an additional HIGH finding.
4. Provides assume-breach remediation: remove the grant, audit CloudTrail
   for decrypt events, re-encrypt affected data, enable rotation.

**End-to-end scenario:** see
[`skills/kms-key-policy-auditor/examples/end-to-end.md`](skills/kms-key-policy-auditor/examples/end-to-end.md)
for a multi-statement key policy walkthrough (root trust + cross-account
decrypt + same-account ViaService) covering severity aggregation, the
root-of-trust exception, and the assume-breach remediation workflow.

---

### 6. sts-cross-account-role-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-sts-cross-account-role`

**What it does:** Audits IAM role trust policies
(AssumeRolePolicyDocument) for cross-account/external trust exposure,
wildcard Principal grants, confused-deputy service-principal vectors, and
condition-strength weaknesses. Emits a deterministic
EXTERNAL_TRUST | WILDCARD_TRUST | CONDITIONAL | OK verdict per role.

**When to invoke (trigger phrases):**

- "who can assume this role?"
- "audit this role trust policy"
- "cross-account role trust"
- "confused deputy", "confused-deputy risk"
- "ExternalId missing"
- "Principal star", "Principal wildcard"
- "service principal trust"
- "SourceArn missing", "SourceAccount condition"
- "SAML federated trust"
- "NotPrincipal trust policy"
- hardening a role trust before production

**Example prompt:**

```
You: "Audit this role's trust policy before we deploy. Role ARN:
     arn:aws:iam::123456789012:role/data-pipeline-access.
     Trust policy: {Principal: {Service: lambda.amazonaws.com},
     Action: sts:AssumeRole}. Is this safe?"
```

**Expected behavior:**

1. Classifies by the 9-step trust-policy decision tree.
2. Emits VERDICT: EXTERNAL_TRUST (Step 4: confused-deputy service principal
   without aws:SourceArn/aws:SourceAccount).
3. Explains the confused-deputy problem: any AWS customer's Lambda function
   can trigger an AssumeRole call via the Lambda service.
4. Provides specific remediation: add aws:SourceArn (ArnLike) +
   aws:SourceAccount (StringEquals) condition.

**End-to-end scenario:** see
[`skills/sts-cross-account-role-auditor/examples/end-to-end.md`](skills/sts-cross-account-role-auditor/examples/end-to-end.md)
for a multi-statement trust-policy walkthrough (same-account CI trust +
unguarded Lambda service principal) covering aggregation, confused-deputy
detection, and the dual SourceArn + SourceAccount remediation.

**Relationship to iam-least-privilege-advisor:** This skill audits the
**trust policy** (who can assume the role). The iam-least-privilege-advisor
audits the **permissions policy** (what the role can do after assuming it).
Both surfaces should be audited for every role.

---

### 7. inspector2-coverage-finding-auditor

**Pipeline phase:** Phase 2 — Audit.

**What it does:** Audits Amazon Inspector2 coverage gaps and finding severity
to determine whether EC2 instances, ECR repositories, and Lambda functions are
effectively scanned and free of exploitable vulnerabilities or
misconfigurations. Classifies each resource into a single
CRITICAL / HIGH / MEDIUM / LOW / COVERED verdict by reasoning over Inspector2
enablement state, per-resource coverage status (SSM-agent dependency for EC2,
scanOnPush for ECR, Lambda code-scanning opt-in), network-reachability
amplification of CVEs, CISA KEV catalog cross-reference, finding lifecycle
(OPEN vs SUPPRESSED), and resource criticality tier.

**Slash command:** `/aws:audit-inspector2-coverage-findings` — or route via `/aws:pipeline`.

**When to invoke (trigger phrases):**

- "are my EC2 instances covered by Inspector2?"
- "what's the severity of these findings?"
- "is this CVE internet-reachable?"
- "check scan coverage before production deployment"
- "SSM agent offline — coverage gap"
- "ECR scanOnPush audit"
- "Lambda code scanning disabled"
- "KEV catalog check"
- "vulnerability posture audit"

**Example prompt:**

```
You: "I have an EC2 instance i-prod-web-01 with an OPEN CRITICAL CVE
     (CVE-2021-44228, log4j) and a NETWORK_REACHABILITY finding showing port
     443 is reachable from the internet. Coverage is ACTIVE. How bad is this?"
```

**Expected behavior:**

1. Applies the 8-step classification logic (coverage -> finding -> aggregation).
2. Emits VERDICT: CRITICAL (internet-reachable critical CVE = confirmed exploitable).
3. Cites the reachability amplification rule and CISA KEV catalog cross-reference.
4. Provides containment-first remediation (restrict SG, then patch via SSM).

**End-to-end scenario:** see
[`skills/inspector2-coverage-finding-auditor/examples/end-to-end.md`](skills/inspector2-coverage-finding-auditor/examples/end-to-end.md)
for a four-resource walkthrough (internet-reachable critical CVE, SSM-offline
coverage gap, Lambda partial coverage, clean ECR) covering reachability
amplification, coverage-tier classification, and account-level aggregation.

---

### 8. guardduty-finding-severity-triage

**Pipeline phase:** Phase 3 — Prioritize.

**Slash command:** `/aws:triage-guardduty-findings`

**What it does:** Classifies Amazon GuardDuty findings into a context-aware
triage severity (CRITICAL | HIGH | MEDIUM | LOW | LIKELY_FALSE_POSITIVE) by
overlaying finding-type threat taxonomy, six false-positive detection
patterns, aggregation counts, and resource criticality on top of
GuardDuty's numeric severity. Flags authorized-scanner port sweeps,
Tor traffic on public-facing services, known-safe DNS domains, and AWS
service-linked role activity as likely false positives.

**When to invoke (trigger phrases):**

- "triage this GuardDuty finding"
- "is this finding a false positive?"
- "GuardDuty severity classification"
- "PortSweepUnusual", "TorIPCaller", "CryptocurrencyClient"
- "SSHBruteForce", "MaliciousIPCaller"
- "should I archive this finding?"
- "suppression filter"
- prioritizing findings for a SOC queue

**Example prompt:**

```
You: /aws:triage-guardduty-findings

     "Finding type: Impact:EC2/CryptocurrencyClient!SSH, Severity: 8.0,
     Resource: i-0prodweb9988, Count: 12. Triage this."
```

**Expected behavior:**

1. Checks false-positive patterns first (authorized scanner, known-safe
   DNS, expected Tor on public service, AWS service role, change window).
2. If not a false positive, classifies by threat category: crypto mining /
   credential exfiltration / confirmed C2 -> CRITICAL; brute force /
   malicious IP / backdoor -> HIGH; behavioral anomaly -> MEDIUM; port
   probe / recon -> LOW.
3. Applies context overlays (count > 50 escalation, resource criticality).
4. Emits VERDICT with specific remediation (IR steps for CRITICAL,
   archival + suppression filter for LIKELY_FALSE_POSITIVE).

**End-to-end scenario:** see
[`skills/guardduty-finding-severity-triage/example/end-to-end.md`](skills/guardduty-finding-severity-triage/example/end-to-end.md)
for a three-finding batch triage walkthrough (CRITICAL crypto mining,
LIKELY_FALSE_POSITIVE scanner, MEDIUM anomalous login) covering
false-positive override, threat-category escalation, and forensic-first
remediation ordering.

---

### 9. cognito-idp-user-pool-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cognito-user-pool`

**CLI route:**

```bash
node cli/bin/cli.js route "audit my Cognito user pool for security"
```

**What it does:** Audits Amazon Cognito user pool configurations for
identity-security posture — MFA enforcement (OFF/OPTIONAL/ON), password
policy strength, app-client auth-flow safety (SRP vs password vs admin),
OAuth flow exposure (implicit vs code+PKCE), token validity,
PreventUserExistenceErrors (user enumeration), Advanced Security Features
mode (OFF/AUDIT/ENFORCED), and deletion protection. Recognizes the
`ADMIN_NO_SRP_AUTH` / `ALLOW_ADMIN_USER_PASSWORD_AUTH` rename, SMS-vs-TOTP
MFA risk, and multi-client aggregation (worst-client-wins).

**When to invoke (trigger phrases):**

- "is this Cognito user pool secure?"
- "check MFA enforcement"
- "audit my app client auth flows"
- "is the OAuth configuration safe?"
- "PreventUserExistenceErrors"
- "implicit flow vs code flow"
- "ALLOW_ADMIN_USER_PASSWORD_AUTH"
- "harden this pool before production"
- reviewing a user pool before production deployment

**Example prompt:**

```
You: "Audit this Cognito pool: MfaConfiguration OFF, password 6 chars no
     complexity, app client uses USER_PASSWORD_AUTH with no secret,
     PreventUserExistenceErrors LEGACY. Is this production-ready?"
```

**Expected behavior:**

1. Classifies the pool: no MFA + weak password + user enumeration + public
   client with password auth.
2. Emits VERDICT: INSECURE (Rule 1a + 1c + 1d — CRITICAL).
3. Identifies the specific risks: account takeover via brute-force,
   user enumeration, credential capture via non-SRP flow.
4. Provides ordered remediation: enable MFA (phased), fix OAuth flows,
   enable PreventUserExistenceErrors, migrate to SRP auth.

**End-to-end scenario:** see
[`skills/cognito-idp-user-pool-auditor/example/end-to-end-audit.md`](skills/cognito-idp-user-pool-auditor/example/end-to-end-audit.md)
for a three-config walkthrough (INSECURE pool with implicit OAuth + legacy
errors, WEAK pool with admin auth flow, fully hardened OK pool) covering
multi-client aggregation, auth-flow strength matrix reasoning, and phased
MFA rollout remediation.

---

### 9. acm-certificate-expiry-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-acm-certificate-expiry`

**CLI route:**

```bash
node cli/bin/cli.js route "check my ACM certificates for expiry"
```

**What it does:** Audits ACM certificates for expiry risk, renewal status
(FAILED_AUTORENEWAL, auto-renewal eligibility), certificate type (AMAZON_ISSUED
vs IMPORTED), validation method (DNS vs email), and key-algorithm strength
(RSA_2048, EC, deprecated RSA_1024). Classifies each certificate into a
deterministic verdict: EXPIRED, EXPIRING_SOON, RENEWAL_FAILED, or OK.

**When to invoke (trigger phrases):**

- "is this certificate about to expire?"
- "ACM certificate renewal failed"
- "FAILED_AUTORENEWAL", "CAA_ERROR"
- "imported certificate expiry"
- "DNS validation CNAME deleted"
- "certificate key algorithm", "RSA_1024"
- "CloudFront certificate region"
- "TLS certificate health", "certificate compliance"
- auditing certificates before production deployment

**Example prompt:**

```
You: "My ACM certificate for api.example.com has NotAfter 2026-07-15
     and Status EXPIRED. What's the impact and how do I fix it?"
```

**Expected behavior:**

1. Computes days_until_expiry from NotAfter (UTC).
2. Checks Status (EXPIRED → terminal), RenewalSummary (FAILED_AUTORENEWAL →
   renewal failure), and Type (IMPORTED uses 60-day threshold vs 30-day for
   AMAZON_ISSUED).
3. Emits VERDICT with risk level and specific remediation (CAA record fix,
   CNAME re-creation, re-import command, re-request with DNS validation).
4. Flags deprecated key algorithms (RSA_1024) even when verdict is OK.

**End-to-end example:** see
[`skills/acm-certificate-expiry-auditor/examples/end-to-end.md`](skills/acm-certificate-expiry-auditor/examples/end-to-end.md)
for a three-certificate audit walkthrough (EXPIRED, RENEWAL_FAILED via CAA_ERROR,
and IMPORTED EXPIRING_SOON) covering type-aware thresholds and CAA-root-cause
diagnosis.

---

### 10. secretsmanager-rotation-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-secretsmanager-rotation` — or route via `/aws:pipeline`.

**What it does:** Audits Secrets Manager secrets for rotation health —
rotation enablement, rotation-Lambda health (existence, execution-role
permissions, VPC connectivity, invocation errors), staleness against the
configured rotation interval, stuck AWSPENDING versions, and recovery-window
state. Classifies each secret as UNROTATED, ROTATION_BROKEN, STALE, or OK
with risk-severity and concrete remediation.

**When to invoke (trigger phrases):**

- "is this secret rotating?"
- "check secret rotation health"
- "rotation Lambda broken"
- "stale secret", "unrotated secret"
- "LastRotatedDate", "AutomaticallyAfterDays"
- "AWSPENDING stuck version"
- "recovery window secret"
- "credential hygiene", "rotation compliance"
- reviewing secret rotation before a compliance gate

**Example prompt:**

```
You: "This RDS secret has RotationEnabled: true but LastRotatedDate is null
     and the rotation Lambda errors with ResourceNotFoundException (DB deleted).
     Is the credential being rotated?"
```

**Expected behavior:**

1. Applies the 8-step classification in dependency-chain order (recovery
   window -> rotation enabled -> Lambda existence -> Lambda invocation ->
   execution-role chain -> AWSPENDING -> freshness -> OK).
2. Emits VERDICT: ROTATION_BROKEN (Step 7a — null LastRotatedDate after
   3 intervals, Lambda erroring on deleted target).
3. Cites the root cause: target RDS instance deleted, Lambda cannot complete
   setSecret step.
4. Provides specific remediation: recreate or retarget the Lambda, then
   trigger manual rotation to verify.

**End-to-end scenario:** see
[`skills/secretsmanager-rotation-auditor/example/README.md`](skills/secretsmanager-rotation-auditor/example/README.md)
for a three-secret audit walkthrough (UNROTATED RDS, ROTATION_BROKEN with
deleted Lambda, OK healthy rotation) covering the full dependency-chain
analysis and remediation workflow.

---

### 11. securityhub-control-compliance-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-securityhub-control-compliance` — or route via `/aws:pipeline`.

**What it does:** Audits AWS Security Hub control compliance findings and maps
each to a deterministic verdict (FAILED | WARNING | PASSED | NOT_APPLICABLE),
then maps every FAILED / WARNING control to a specific fix action. Handles the
full finding lifecycle — active findings, suppressed failures, resolved-but-
still-failing, archived findings, NOT_AVAILABLE with StatusReasons splitting,
and multi-account aggregation across FSBP / CIS / PCI-DSS / NIST 800-53
standards.

**When to invoke (trigger phrases):**

- "security hub compliance status"
- "triage these security hub findings"
- "is this control failing or just suppressed?"
- "NOT_AVAILABLE finding — does it apply?"
- "StatusReasons code"
- "FSBP control", "CIS benchmark control"
- "compliance gap report"
- "fix action for this control"
- preparing for a quarterly compliance review or audit

**Example prompt:**

```
You: "This Security Hub finding for EC2.15 has Compliance.Status FAILED but
     Workflow.Status SUPPRESSED with no note. What's the real compliance
     posture?"
```

**Expected behavior:**

1. Applies the 8-step classification in lifecycle order (ARCHIVED -> SUPPRESSED
   -> RESOLVED -> NOT_AVAILABLE split -> FAILED -> WARNING -> PASSED).
2. Emits VERDICT: WARNING (Rule 2 — suppressed FAILED is a governance concern,
   not a pass).
3. Identifies the missing suppression note and the stale age (>60 days).
4. Provides specific remediation: review the suppression, unsuppress if the
   compensating control is no longer valid, then restrict the SG rule.

**End-to-end scenario:** see
[`skills/securityhub-control-compliance-auditor/example/end-to-end-audit.md`](skills/securityhub-control-compliance-auditor/example/end-to-end-audit.md)
for a five-finding audit walkthrough covering all four verdicts (FAILED, PASSED,
NOT_APPLICABLE, WARNING) with aggregate rollup and the full remediation workflow.

---

### 12. wafv2-web-acl-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-wafv2-web-acl`

**CLI route:**

```bash
node cli/bin/cli.js route "audit my WAF web acl"
```

**What it does:** Audits WAFv2 Web ACL configurations to determine whether the
ACL provides effective protection: default-action posture (Allow vs Block),
managed-rule-group coverage gaps, rule effectiveness (BLOCK vs COUNT, shadow
rules, stale exclusions), rate-based rule correctness, logging and visibility
configuration, and text-transformation bypass vectors. Emits a deterministic
verdict (MISCONFIGURED | WEAK | ADEQUATE | OK) per Web ACL.

**When to invoke (trigger phrases):**

- "audit my WAF"
- "WAFv2 web acl"
- "check managed-rule coverage"
- "are my WAF rules in count mode?"
- "shadow rule bypass"
- "rate-based rule behind CloudFront"
- "WAF logging"
- "OWASP WAF", "hardening WAF before production"
- reviewing a WAF before production deployment

**Example prompt:**

```
You: "Audit this WAF before we go to production. DefaultAction is Allow,
     CommonRuleSet and SQLiRuleSet are in BLOCK, but there's a custom
     Allow rule at priority 0 matching /api/."
```

**Expected behavior:**

1. Applies the 11-step classification logic in declaration order.
2. Emits VERDICT: MISCONFIGURED (Step 2: shadow rule bypasses managed
   inspection for all /api/ traffic).
3. Cites the priority-ordering bypass and the compound gaps (no rate rule,
   no logging).
4. Provides specific remediation: reprioritize the shadow rule, add a
   FORWARDED_IP rate-based rule, enable logging.

**End-to-end example:** see
[`skills/wafv2-web-acl-auditor/examples/end-to-end.md`](skills/wafv2-web-acl-auditor/examples/end-to-end.md)
for a shadow-bypass-rule walkthrough covering priority-ordering analysis,
COUNT-mode detection, and the safe BLOCK-mode progression.

---

### 13. accessanalyzer-finding-triage

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:triage-accessanalyzer-findings` — or route via `/aws:pipeline`.

**What it does:** Triages IAM Access Analyzer findings (external access +
unused access) into risk verdicts with remediation. Classifies each finding as
EXTERNAL_ACCESS (real exposure), UNUSED_ACCESS (stale identity/credential),
EXPECTED (known cross-account or service integration), or SAFE (condition-
bounded non-risk). Evaluates the zone-of-trust model, principal type (public
vs specific vs service), condition-key cryptographic strength, resource-type
blast radius, and finding freshness.

**When to invoke (trigger phrases):**

- "triage this Access Analyzer finding"
- "is this external access finding a real risk?"
- "should I archive this finding?"
- "unused IAM role", "unused access key"
- "isPublic finding"
- "zone of trust", "cross-account resource policy"
- "service principal finding"
- "is this cross-account access expected?"
- "archive rule suppression"

**Example prompt:**

```
You: /aws:triage-accessanalyzer-findings

     "Finding type: ExternalAccess, Resource: AWS::KMS::Key,
     Principal: '*', isPublic: true, Actions: kms:Decrypt,
     Condition: {}. What's the risk?"
```

**Expected behavior:**

1. Routes by finding type (ExternalAccess vs Unused*).
2. For external access: evaluates condition strength (cryptographic vs
   forgeable), classifies principal type, applies resource-type severity
   matrix, checks expected service integrations.
3. Emits VERDICT: EXTERNAL_ACCESS / CRITICAL (KMS decrypt is a data-access
   multiplier).
4. Provides incident-response remediation with CloudTrail audit for the
   exposure window.

**End-to-end example:** see
[`skills/accessanalyzer-finding-triage/example/README.md`](skills/accessanalyzer-finding-triage/example/README.md)
for a four-finding batch triage walkthrough (KMS public CRITICAL, S3
condition-bounded SAFE, unused stale role, Lambda service principal EXPECTED)
covering condition-strength classification, service-integration recognition,
and prioritized remediation.

---

### 14. ecs-task-definition-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ecs-task-definition`

**What it does:** Audits ECS task definitions for privileged containers,
plaintext secrets in environment variables (instead of Secrets Manager / SSM),
host network mode, root-user execution, and missing resource limits (CPU,
memory, logging). Emits a deterministic verdict
(PRIVILEGED | SECRET_LEAK | INSECURE | CONFIG_GAP | OK) per task definition
with enumerated findings and specific remediation.

**When to invoke (trigger phrases):**

- "audit this ECS task definition"
- "is my ECS container privileged?"
- "check ECS task for secrets in env vars"
- "ECS host network mode"
- "is my container running as root?"
- "ECS resource limits missing"
- "harden my Fargate task"
- reviewing a task definition before production deployment

**Example prompt:**

```
You: "This ECS task has privileged: true, DATABASE_PASSWORD in environment,
     and networkMode host. Audit it before we migrate to Fargate."
```

**Expected behavior:**

1. Classifies the privileged flag (PRIVILEGED on EC2 — full host kernel
   access), the plaintext secret (SECRET_LEAK), and the insecure network
   mode + root user (INSECURE).
2. Emits VERDICT: PRIVILEGED (worst finding wins — Step 1).
3. Identifies the secret leak and insecure configuration as additional
   findings.
4. Provides register-new-revision remediation: set privileged: false,
   move secret to secrets array (rotate the credential), change to
   awsvpc network mode, set non-root user, add resource limits.

**End-to-end scenario:** see
[`skills/ecs-task-definition-auditor/examples/end-to-end.md`](skills/ecs-task-definition-auditor/examples/end-to-end.md)
for a multi-finding legacy EC2 task definition walkthrough (privileged +
secret leak + host network + root user + no limits + dangerous
capabilities) covering severity aggregation and the register-new-revision
remediation workflow.

---

### 15. eks-cluster-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-eks-cluster`

**What it does:** Audits AWS EKS cluster configurations for public API
endpoint exposure, disabled control-plane logging, IAM auth mapRoles
misconfiguration (system:masters to broad principals, node IAM role
privilege escalation, wildcard username), security group ingress exposure
on critical ports (kubelet 10250, API 443, SSH 22), and outdated Kubernetes
version drift. Emits a deterministic categorical verdict
(PUBLIC_ENDPOINT | LOGGING_DISABLED | CONFIG_GAP | OUTDATED | OK) per
cluster with enumerated findings and specific remediation.

**When to invoke (trigger phrases):**

- "audit this EKS cluster"
- "is my EKS API server public"
- "check control-plane logging"
- "audit aws-auth ConfigMap"
- "system:masters mapping"
- "check EKS security groups"
- "is my Kubernetes version outdated"
- "harden EKS cluster"
- reviewing an EKS cluster before production deployment or compliance audit

**Example prompt:**

```
You: "Audit this EKS cluster before our compliance review. The API
     endpoint is public with publicAccessCidrs empty, logging is off,
     and the node IAM role is in system:masters. What's the risk?"
```

**Expected behavior:**

1. Applies the priority-ordered classification (endpoint -> logging ->
   config -> version).
2. Emits VERDICT: PUBLIC_ENDPOINT (Step 1 — empty publicAccessCidrs
   defaults to 0.0.0.0/0).
3. Lists all other findings (LOGGING_DISABLED, CONFIG_GAP for node-role
   escalation, OUTDATED if applicable) in the FINDINGS section.
4. Provides specific remediation with CLI commands for each finding.

**End-to-end scenario:** see
[`skills/eks-cluster-auditor/examples/end-to-end.md`](skills/eks-cluster-auditor/examples/end-to-end.md)
for a multi-finding cluster walkthrough (public endpoint, disabled logging,
node-role privesc, open kubelet port, outdated version) covering
priority-ordered classification, the empty-CIDR trap, and the
multi-finding remediation workflow.

---

### 16. lambda-runtime-deprecation-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-lambda-runtime-deprecation`

**What it does:** Audits AWS Lambda functions for deprecated/EOL runtimes
(python3.9, nodejs16.x, etc.), over-permissioned execution roles (admin
wildcards, privilege-escalation actions), public function URL exposure
(AuthType NONE), and observability config gaps (missing X-Ray tracing,
missing DLQ, reserved concurrency 0). Emits a deterministic verdict
(DEPRECATED_RUNTIME | PUBLIC_EXPOSURE | OVERPERMISSIVE | CONFIG_GAP | OK)
per function with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit this Lambda function"
- "is my Lambda runtime deprecated?"
- "Lambda runtime EOL"
- "check Lambda execution role"
- "Lambda admin role"
- "is my function URL public?"
- "Lambda AuthType NONE"
- "missing X-Ray tracing Lambda"
- "Lambda dead letter queue"
- "hardening Lambda function"
- reviewing a Lambda function before production deployment

**Example prompt:**

```
You: "This Lambda function runs python3.9 with a scoped S3 role, active
     tracing, and no function URL. Is it production-ready?"
```

**Expected behavior:**

1. Compares Runtime (python3.9) against the supported-runtime set.
2. Emits VERDICT: DEPRECATED_RUNTIME (Step 1 — python3.9 is deprecated,
   Phase 1 create/update block in effect; function is a ticking time bomb).
3. Confirms the execution role, tracing, and URL are all OK — the runtime
   is the sole finding.
4. Provides specific remediation: update to python3.12, test code
   compatibility, publish a new version.

**End-to-end scenario:** see
[`skills/lambda-runtime-deprecation-auditor/examples/end-to-end.md`](skills/lambda-runtime-deprecation-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (nodejs16.x blocked Phase 2 + public
function URL) covering worst-finding aggregation, runtime lifecycle phases,
and the stale-LastModified risk amplifier.

---

### 17. compute-optimizer-findings-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-compute-optimizer-findings`

**What it does:** Audits AWS Compute Optimizer findings for EC2, EBS, Lambda,
and Auto Scaling Group resources — classifies overprovisioned (underutilized)
cost waste, underprovisioned (performance-risk) findings, and low-confidence
recommendations (inferred memory without CWAgent, high performanceRisk, stale
findings, zero-invocation Lambda) into a deterministic verdict with per-finding
risk and CLI remediation. Emits UNDERUTILIZED | NOT_OPTIMIZED | OK per resource.

**When to invoke (trigger phrases):**

- "audit compute optimizer findings"
- "check EC2 right-sizing recommendations"
- "is this compute optimizer finding reliable"
- "overprovisioned instances"
- "Lambda memory recommendations"
- "EBS volume recommendations"
- "performanceRisk too high"
- "compute optimizer low confidence"
- "right-size EC2 instances"
- reviewing cost-optimization posture before a batch right-size

**Example prompt:**

```
You: "This EC2 instance has a Compute Optimizer finding of Overprovisioned
     with CPU at 8% and Memory at 15% (CWAgent installed). performanceRisk 1,
     savings $150/month. Should I right-size?"
```

**Expected behavior:**

1. Applies the confidence gate first — checks whether Memory metrics are
   measured (CWAgent present) vs inferred, evaluates performanceRisk, checks
   data sufficiency and staleness.
2. Emits VERDICT: UNDERUTILIZED (Overprovisioned + HIGH confidence + savings
   > $100/month = actionable cost waste).
3. Quantifies waste ($150/month) and risk-tier it HIGH.
4. Provides CLI remediation: create AMI, stop, modify-instance-attribute,
   start, monitor 7 days.

**End-to-end scenario:** see
[`skills/compute-optimizer-findings-auditor/examples/end-to-end.md`](skills/compute-optimizer-findings-auditor/examples/end-to-end.md)
for a two-instance walkthrough (high-confidence UNDERUTILIZED vs low-confidence
NOT_OPTIMIZED with inferred memory) covering confidence gating,
performanceRisk interpretation, and per-resource CLI remediation.

---

## Pipeline Walkthrough (end-to-end)

```
You: "/aws:pipeline — I'm onboarding a new account, audit everything."

Orchestrator:
  [Phase: Assess | Resources: starting inventory | Skills routed: all]

  Phase 1 — Assess:
  - s3-public-access-auditor discovers 15 buckets, 3 with BPA off
  - iam-least-privilege-advisor discovers 8 roles, 2 with wildcard actions
  - ec2-security-group-auditor discovers 12 SGs, 4 with 0.0.0.0/0 rules

  [Phase: Audit | Resources: 15 buckets, 8 roles, 12 SGs | Skills routed: all]

  Phase 2 — Audit:
  - s3: 2 PUBLIC (write-open CRITICAL), 1 AMBIGUOUS, 12 SAFE
  - iam: 3 OVERPERMISSIVE, 4 LEAST_PRIVILEGE, 1 AMBIGUOUS
  - ec2: 2 OPEN (SSH+RDP to 0.0.0.0/0), 2 PUBLIC_NONCRITICAL, 8 RESTRICTED

  [Phase: Prioritize | Findings: 2 CRITICAL, 5 HIGH, 2 MEDIUM | Skills routed: orchestrator]

  Phase 3 — Prioritize:
  1. CRITICAL: S3 write-open bucket (data destruction risk) — fix NOW
  2. CRITICAL: S3 write-open bucket #2 — fix NOW
  3. HIGH: SSH open to internet (CIS 4.1) — fix today
  4. HIGH: RDP open to internet (CIS 4.2) — fix today
  5. HIGH: IAM PassRole on * (privilege escalation) — fix today
  ...

  [Phase: Remediate | Findings: 2 CRITICAL prioritized | Skills routed: s3-public-access-auditor]

  Phase 4 — Remediate:
  - S3 CRITICAL: enable BPA immediately (incident response), then audit CloudTrail
  - EC2: restrict SSH/RDP to known CIDR or use Session Manager
  - IAM: scope down PassRole to specific role ARNs
```

---

### 17. autoscaling-group-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-autoscaling-group`

**What it does:** Audits AWS Auto Scaling Groups for launch-template health
(legacy launch configuration, IMDSv2 enforcement), ELB health-check integrity
(missing target group, grace-period timing), mixed-instances policy (single
Spot instance type, allocation strategy), capacity bounds (desired vs
min/max), and unhealthy-termination behavior (EC2-only checks behind an ELB,
capacity rebalance). Emits a deterministic verdict
(MISCONFIGURED | CONFIG_GAP | OK) per ASG with enumerated findings and
specific remediation.

**When to invoke (trigger phrases):**

- "audit this auto scaling group"
- "is my ASG misconfigured?"
- "why are my instances cycling?"
- "check ASG health check wiring"
- "launch template vs launch configuration"
- "spot single instance type"
- "ASG infinite replacement loop"
- "is my Spot diversification sufficient?"

**Example prompt:**

```
You: "This ASG has HealthCheckType ELB but no target group attached.
     Instances keep cycling. What's wrong?"
```

**Expected behavior:**

1. Classifies the ELB health check as MISCONFIGURED (Step 3) — no target
   group means every instance is Unhealthy from launch, creating an infinite
   replacement loop.
2. Evaluates all other dimensions (launch template IMDSv2, capacity bounds,
   MIP diversification, AZ diversity, scale-out headroom).
3. Emits VERDICT: MISCONFIGURED with per-finding breakdown.
4. Provides specific remediation: attach the target group or switch to EC2
   health checks, with exact CLI commands.

**End-to-end scenario:** see
[`skills/autoscaling-group-auditor/examples/end-to-end.md`](skills/autoscaling-group-auditor/examples/end-to-end.md)
for a production ASG walkthrough (ELB health check with no target group)
covering the infinite-replacement-loop concept, ordered classification, and
per-finding CLI remediation.

---

---

### 18. ecr-repository-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ecr-repository` — or route via `/aws:pipeline`.

**What it does:** Audits ECR private repositories for public-access exposure
via `repositoryPolicy` (`Principal: "*"` with pull/push actions and no strong
condition), image-scan configuration gaps (`scanOnPush: false` with unscanned
images), lifecycle-policy absence (no `lifecyclePolicyText`), tag-immutability
gaps (`MUTABLE` tags — supply-chain overwrite risk), and cross-account access.
Classifies each repository as PUBLIC, NO_SCAN, NO_LIFECYCLE, CONFIG_GAP, or OK
with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this ECR repository"
- "is my ECR repo public?"
- "check ECR repository policy"
- "is scan-on-push enabled?"
- "does this repo have a lifecycle policy?"
- "are there unscanned images?"
- "is tag immutability set?"
- "ECR cross-account access"

**Example session:**

You: "This ECR repo grants ecr:BatchGetImage to Principal '*' with no
condition. scanOnPush is false."

Skill:
1. Classifies the repositoryPolicy statement: WILDCARD_PRINCIPAL + PULL
   actions + no condition → PUBLIC (any AWS account holder can pull every
   image layer, exposing source code and embedded secrets).
2. Checks scanOnPush: false + images with imageScanStatus: null → NO_SCAN.
3. Emits VERDICT: PUBLIC (worst finding wins).
4. Remediation: remove the wildcard principal, enable scanOnPush, manually
   scan existing images, assume breach and audit CloudTrail for pull events.

**End-to-end example:** see
[`skills/ecr-repository-auditor/examples/end-to-end.md`](skills/ecr-repository-auditor/examples/end-to-end.md)
for a four-finding audit walkthrough (PUBLIC pull grant, NO_SCAN with
unscanned images, NO_LIFECYCLE, CONFIG_GAP mutable tags) covering severity
aggregation, image-layer exposure reasoning, and assume-breach remediation.

---

### 19. efs-filesystem-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-efs-filesystem`

**What it does:** Audits EFS filesystems for encryption-at-rest, filesystem
policy public principal exposure, encryption-in-transit enforcement
(`aws:SecureTransport`), lifecycle management policies, and access point
governance. Emits a deterministic verdict (UNENCRYPTED | PUBLIC_POLICY |
CONFIG_GAP | OK) per filesystem with enumerated findings and specific
remediation.

**When to invoke (trigger phrases):**

- "audit this EFS filesystem"
- "is my EFS filesystem public"
- "check EFS encryption"
- "EFS filesystem policy too permissive"
- "review EFS lifecycle policy"
- "EFS access points configured"
- "harden EFS filesystem"
- reviewing an EFS filesystem before production deployment

**Example prompt:**

```
You: "This EFS filesystem has Principal * with ClientRootAccess in the
     policy, no lifecycle policy, and no TLS enforcement. What's the risk?"
```

**Expected behavior:**

1. Classifies the filesystem as PUBLIC_POLICY (Principal "*" with Client*
   actions and no restrictive condition — Rule 2a).
2. Notes ClientRootAccess as total filesystem compromise (no root squashing).
3. Identifies lifecycle and TLS gaps as additional CONFIG_GAP findings.
4. Provides assume-breach remediation: restrict principals, add conditions,
   enforce TLS, add lifecycle policy, create access points.

**End-to-end scenario:** see
[`skills/efs-filesystem-auditor/examples/end-to-end.md`](skills/efs-filesystem-auditor/examples/end-to-end.md)
for a production ML-dataset filesystem walkthrough (public root access +
missing lifecycle + missing TLS) covering severity aggregation, the
ClientRootAccess danger concept, and the assume-breach remediation workflow.

---

### 20. backup-plan-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-backup-plan`

**What it does:** Audits AWS Backup plans for coverage gaps (empty or missing
resource selections), vault risks (missing vault lock, governance-mode lock
bypassable by root, AWS-managed encryption key), impossible lifecycle
configurations (cold storage transition at or after deletion, retention below
vault-lock floor), and compliance violations (backup frequency below daily,
retention below 30 days). Emits a deterministic verdict
(COVERAGE_GAP | VAULT_RISK | NONCOMPLIANT | CONFIG_GAP | OK) per plan with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this backup plan"
- "check backup coverage"
- "is my backup vault locked?"
- "backup lifecycle invalid"
- "cold storage transition"
- "vault lock governance vs compliance"
- "backup retention too short"
- "ransomware protection backup"
- reviewing a backup plan before production deployment

**Example prompt:**

```
You: "This backup plan has MoveToColdStorageAfterDays: 90 and
     DeleteAfterDays: 30. Is the lifecycle valid?"
```

**Expected behavior:**

1. Classifies the lifecycle as impossible — cold storage transition (90) is
   at or after deletion (30), so the cold tier is never used (Step 1a).
2. Emits VERDICT: CONFIG_GAP — the first matching step in the ordered
   classification.
3. Reports vault, coverage, and schedule dimensions as OK (they pass their
   respective steps but CONFIG_GAP takes priority).
4. Provides lifecycle-fix remediation: set cold=30, delete=90, with CLI.

**End-to-end scenario:** see
[`skills/backup-plan-auditor/examples/end-to-end.md`](skills/backup-plan-auditor/examples/end-to-end.md)
for a production EFS backup walkthrough covering the impossible-lifecycle
concept, ordered classification priority, and cross-region copy assessment.

---

### 21. dlm-lifecycle-policy-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-dlm-lifecycle-policy`

**What it does:** Audits AWS Data Lifecycle Manager (DLM) EBS snapshot
lifecycle policies for coverage gaps and silent-failure modes. Checks for
disabled policies (State: DISABLED creates zero snapshots), empty tag/resource
targets (TargetTags: [] matches no volumes), invalid schedules (5-field cron
is rejected; DLM requires 6-field with year), missing/weak retention
(Count:1 = no recovery history; missing RetainRule = unbounded quota cliff),
absent cross-region copy (single-region backup = no DR), CopyTags metadata
loss, and per-volume snapshot quota risk (Count >= 1000). Emits a
deterministic verdict (NO_POLICY | MISCONFIGURED | CONFIG_GAP | OK) per policy
or workload with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit this DLM lifecycle policy"
- "why did my EBS snapshots stop?"
- "is my DLM policy enabled?"
- "check DLM retention and DR"
- "is DLM actually working?"
- "EBS backup coverage"
- "DLM silent failure"
- reviewing a DLM policy before production deployment

**Example prompt:**

```
You: "This DLM policy is ENABLED with a daily schedule and 14-snapshot
     retention, but there's no cross-region copy. What's the gap?"
```

**Expected behavior:**

1. Classifies the policy State (ENABLED), target coverage (valid TargetTags),
   schedule validity (valid Interval), and retention strength (14 snapshots
   = sensible).
2. Identifies the missing CrossRegionCopyTargets as a DR gap (Step 7).
3. Emits VERDICT: CONFIG_GAP — single-region backup provides no disaster
   recovery posture.
4. Provides remediation: add a CrossRegionCopyTarget with an explicit KMS
   CMK in the DR region (do NOT rely on the destination region's default
   encryption), then verify DR snapshots via `describe-snapshots`.

**End-to-end scenario:** see
[`skills/dlm-lifecycle-policy-auditor/examples/end-to-end.md`](skills/dlm-lifecycle-policy-auditor/examples/end-to-end.md)
for a six-scenario walkthrough covering NO_POLICY (account with zero
policies), MISCONFIGURED (disabled policy + empty TargetTags), CONFIG_GAP
(no DR + weak retention with CopyTags false), and OK (clean production
policy with 6-field cron, 30-day retention, and cross-region copy).

---

### 22. ebs-volume-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ebs-volume`

**What it does:** Audits EBS volumes and snapshots for unencrypted state
(compliance violation under PCI/HIPAA/SOC2), unattached cost-waste volumes,
legacy volume types (gp2/io1/standard with online upgrade paths), stale
snapshots accumulating storage cost (with Fast Snapshot Restore cost-
dominance check), and public snapshots exposing block-level data to every
AWS account. Emits a deterministic verdict
(UNENCRYPTED | UNATTACHED | LEGACY_TYPE | STALE_SNAPSHOT | PUBLIC_SNAPSHOT | OK)
per resource with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this EBS volume"
- "is my EBS volume encrypted"
- "unattached EBS volumes"
- "gp2 to gp3 upgrade"
- "io1 to io2 upgrade"
- "stale EBS snapshots"
- "public snapshot exposure"
- "CreateVolumePermission public"
- "EBS cost optimization"
- "EBS compliance violation"
- reviewing an EBS volume or snapshot before production deployment or a
  compliance audit

**Example prompt:**

```
You: "This EBS volume is unencrypted, gp2, and attached with
     DeleteOnTermination: true. It hosts our checkout config. PCI audit
     next week — what's the verdict and remediation?"
```

**Expected behavior:**

1. Classifies the volume as UNENCRYPTED (HIGH) — Step 1, the worst
   non-CRITICAL verdict. Cites PCI-DSS Requirement 3.4 explicitly.
2. Notes the DeleteOnTermination: true as a CONFIG_GAP finding inside the
   verdict (does not change the verdict; not in the enum).
3. Identifies gp2 as LEGACY_TYPE (LOW) and the region's missing
   encryption-by-default as an account-level CONFIG_GAP.
4. Provides the correct 7-step encryption-migration flow (snapshot →
   copy-snapshot --encrypted → create-volume → attach → fix
   DeleteOnTermination → detach → delete). Does NOT recommend
   "enable encryption" — EBS encryption is immutable per resource.
5. Surfaces `enable-ebs-encryption-by-default` as the higher-leverage
   account-level remediation (do this FIRST to stop future bleeding).

**End-to-end scenario:** see
[`skills/ebs-volume-auditor/examples/end-to-end.md`](skills/ebs-volume-auditor/examples/end-to-end.md)
for a PCI-DSS audit walkthrough (unencrypted gp2 data volume with
DeleteOnTermination: true) covering severity aggregation, the
encryption-immutability remediation flow, account-level root-cause
escalation, and the assume-breach snapshot-lineage workflow.

---

### 23. cur-cost-usage-report-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cur-cost-usage-report` — or route via `/aws:pipeline`.

**What it does:** Audits AWS Cost and Usage Report (CUR) configurations for
FinOps data pipeline health. Checks whether CUR is configured at all (NO_CUR),
whether data is fresh (STALE — hourly manifest > 48h, daily > 72h), and for
configuration gaps (CONFIG_GAP — wrong report version, CSV/GZIP format
blocking Athena, missing ATHENA artifact, S3 versioning disabled, missing
Resources schema element, RefreshClosedReports false). Emits a deterministic
verdict (NO_CUR | STALE | CONFIG_GAP | OK) per report definition.

**When to invoke (trigger phrases):**

- "audit this Cost and Usage Report"
- "is my CUR healthy?"
- "check CUR Athena integration"
- "why is my CUR stale?"
- "CUR not delivering to S3"
- "Athena cost query empty"
- "CUR report version check"
- "is hourly refresh enabled"
- "FinOps data pipeline audit"
- reviewing CUR before a cost-optimization initiative

**Example prompt:**

```
You: "Our hourly CUR hasn't delivered in 9 days and Athena queries
     return empty. The format is CSV/GZIP. What's wrong?"
```

**Expected behavior:**

1. Classifies freshness: 9-day-old manifest for hourly cadence exceeds
   the 48h staleness threshold (Step 2a).
2. Emits VERDICT: STALE — delivery pipeline has stopped.
3. Enumerates all CONFIG_GAP findings: CSV/GZIP blocks Athena (Step 3b),
   no ATHENA artifact (Step 3c), versioning state.
4. Provides specific remediation: diagnose delivery stall, switch to
   Parquet, add ATHENA artifact, run crawler CFN template.

**End-to-end scenario:** see
[`skills/cur-cost-usage-report-auditor/examples/end-to-end.md`](skills/cur-cost-usage-report-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (stale delivery + CSV format + no Athena +
no versioning + RefreshClosedReports false) covering ordered classification,
staleness thresholds, and the per-dimension remediation workflow.

---

### 23. elbv2-load-balancer-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-elbv2-load-balancer`

**What it does:** Audits AWS ELBv2 load balancers (ALB/NLB) for insecure TLS
listener policies (TLS 1.0/1.1, weak ciphers, cleartext HTTP with no HTTPS
redirect), disabled access logs, permissive security groups (all-ports-open,
internal-LB-exposed-to-internet), idle load balancers (zero healthy targets),
disabled cross-zone load balancing (NLB only — ALB cross-zone is always on),
and missing deletion protection. Emits a deterministic categorical verdict
(INSECURE_LISTENER | NO_ACCESS_LOGS | PERMISSIVE_SG | IDLE | CONFIG_GAP | OK)
per load balancer with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this load balancer"
- "check ALB TLS policy"
- "is my NLB secure"
- "load balancer access logs disabled"
- "permissive security group ALB"
- "idle load balancer no targets"
- "cross-zone load balancing NLB"
- "deletion protection load balancer"
- "ELBSecurityPolicy TLS 1.0"
- "ELBSecurityPolicy-2016-08"
- reviewing an ALB or NLB before production deployment or a compliance audit

**Example prompt:**

```
You: "This ALB uses ELBSecurityPolicy-2016-08 on its HTTPS listener and
     access logs are disabled. PCI-DSS audit next week — what's the risk?"
```

**Expected behavior:**

1. Classifies the SslPolicy: ELBSecurityPolicy-2016-08 includes TLS 1.0/1.1
   — deprecated by PCI-DSS, vulnerable to protocol-downgrade attacks.
2. Emits VERDICT: INSECURE_LISTENER (Step 1 — worst finding wins).
3. Identifies the access-logs gap as an additional HIGH finding (Step 3).
4. Provides CLI remediation: modify-listener SslPolicy to
   ELBSecurityPolicy-TLS13-1-2-2021-06, enable access logs with
   modify-load-balancer-attributes.

**End-to-end scenario:** see
[`skills/elbv2-load-balancer-auditor/examples/end-to-end.md`](skills/elbv2-load-balancer-auditor/examples/end-to-end.md)
for a PCI-DSS audit walkthrough (TLS 1.0 default policy + disabled access
logs) covering verdict aggregation, the default-policy-is-insecure insight,
and the per-verdict CLI remediation workflow.

---

### 24. route53-record-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-route53-records` — or route via `/aws:pipeline`.

**What it does:** Audits Route 53 record sets for missing health checks on
routing-policy records (failover, weighted, latency, geolocation, multivalue),
dangling ALIAS targets pointing to deleted AWS resources (ELB, CloudFront, S3
website, API Gateway), DNSSEC signing gaps on public hosted zones, private-IP
exposure in public zones, and TTL inconsistency within routing groups. Emits a
deterministic verdict (NO_HEALTH_CHECK | DNSSEC_GAP | DANGLING | CONFIG_GAP | OK)
per record with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit these Route 53 records"
- "is my DNS failover configured correctly?"
- "dangling DNS record"
- "missing health check on failover"
- "DNSSEC not enabled"
- "public hosted zone exposure"
- "Route 53 TTL inconsistency"
- "subdomain takeover risk"
- reviewing Route 53 records before production deployment or traffic surge

**Example prompt:**

```
You: "Our failover PRIMARY for api.example.com has no health check.
     Is that a problem? The zone also doesn't have DNSSEC."
```

**Expected behavior:**

1. Classifies the failover PRIMARY as NO_HEALTH_CHECK/CRITICAL (Step 2a) —
   Route 53 can never detect primary failure; failover is functionally
   disabled.
2. Notes the DNSSEC gap as an additive HIGH finding (Step 3a) —
   cache-poisoning susceptibility.
3. Recognises that failover SECONDARY without health check is valid
   fail-open behaviour (not flagged as NO_HEALTH_CHECK).
4. Provides remediation: create-health-check, change-resource-record-sets
   UPSERT, enable-hosted-zone-dnssec + create-key-signing-key + publish DS
   record at registrar.

**End-to-end scenario:** see
[`skills/route53-record-auditor/examples/end-to-end.md`](skills/route53-record-auditor/examples/end-to-end.md)
for a pre-traffic-surge audit walkthrough (failover PRIMARY without health
check + dangling CloudFront ALIAS + DNSSEC gap) covering severity aggregation,
the failover-disabled insight, and the assume-takeover remediation workflow.

---

### 24. cloudfront-distribution-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cloudfront-distribution`

**CLI route:**

```bash
node cli/bin/cli.js route "audit my CloudFront distribution"
```

**What it does:** Audits CloudFront distributions for insecure TLS viewer
minimum protocol versions (TLSv1.2_2021 threshold — the year suffix is the
cipher policy, not the TLS version), viewer protocol policy (allow-all),
custom origin protocol (http-only / match-viewer), S3 website endpoint
origins (forces public bucket), missing Origin Access Control on S3 origins
(OAC vs legacy OAI distinction), missing WAF Web ACL association, disabled
access logging, absent geographic restrictions, and empty default root
object. Emits a deterministic verdict
(INSECURE_TLS | NO_OAC | CONFIG_GAP | OK) per distribution.

**When to invoke (trigger phrases):**

- "audit this CloudFront distribution"
- "is my CloudFront TLS secure"
- "check CloudFront OAC"
- "is OAC configured on my S3 origin"
- "does my distribution have a WAF"
- "CloudFront logging disabled"
- "geo restriction CloudFront"
- "ViewerProtocolPolicy allow-all"
- "OriginProtocolPolicy http-only"
- "S3 website endpoint origin"
- "hardening CloudFront before production"

**Example prompt:**

```
You: "This distribution uses TLSv1.2_2019 minimum protocol, the S3 origin
     has no OAC, and logging is disabled. Marketing site launch is tomorrow
     — what's the verdict and remediation?"
```

**Expected behavior:**

1. Classifies as INSECURE_TLS — TLSv1.2_2019 still permits CBC-mode ciphers;
   TLSv1.2_2021 restricts to AEAD-only (Step 2).
2. Also flags NO_OAC — S3 origin with no OAC and no OAI means the bucket
   must be publicly readable (Step 5).
3. Cites the CONFIG_GAP items (no WAF, no logging) as additional findings.
4. Provides CLI remediation: update MinimumProtocolVersion, create OAC and
   attach to origin, update S3 bucket policy, enable logging.

**End-to-end scenario:** see
[`skills/cloudfront-distribution-auditor/examples/end-to-end.md`](skills/cloudfront-distribution-auditor/examples/end-to-end.md)
for a marketing-site launch audit (TLSv1.2_2019 + no OAC + no logging)
covering cipher-suite-difference reasoning, the OAI-vs-OAC migration
workflow, and per-verdict CLI remediation.

---

### 25. billing-account-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-billing-account`

**What it does:** Audits an AWS account's billing posture across five
dimensions — root account security (MFA enabled, zero access keys), IAM
user/group billing access delegation vs root-only, Cost Anomaly Detection
enablement, billing budgets/alerts coverage, and free-tier usage alerts.
Emits a deterministic verdict
(ROOT_BILLING | NO_ANOMALY_DETECTION | CONFIG_GAP | OK) per account with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit my billing configuration"
- "check billing access"
- "is Cost Anomaly Detection enabled"
- "do I have billing budgets"
- "is root MFA enabled"
- "billing alerts configured"
- "free tier usage alerts"
- "who can access billing"
- "root account billing access"
- "root access keys present"
- "FinOps audit"
- reviewing an account's billing posture before a FinOps compliance review

**Example prompt:**

```
You: "This account has root MFA on, IAM billing access activated,
     Cost Explorer enabled, one CAD monitor, one budget at $5000, and
     free-tier alerts on. But I just found a root access key — what's
     the billing verdict?"
```

**Expected behavior:**

1. Classifies the account as ROOT_BILLING (CRITICAL) — Step 1, because
   root access keys bypass MFA for every billing API call. This is the
   single most dangerous billing configuration and trumps all other
   dimensions.
2. Notes that root MFA being enabled is OK but irrelevant for API attacks
   using the access key — MFA protects console sign-in only.
3. Acknowledges the good configuration on all other dimensions (IAM
   delegation active, CAD with subscription, budget with alert, free-tier
   alerts on) as OK findings.
4. Provides the correct remediation: sign in as root in the console to
   delete the key (root keys cannot be managed by IAM users via CLI),
   then audit CloudTrail for `userIdentity.type: "Root"` billing API
   calls during the exposure window.

**End-to-end scenario:** see
[`skills/billing-account-auditor/examples/end-to-end.md`](skills/billing-account-auditor/examples/end-to-end.md)
for a FinOps compliance audit walkthrough (root access keys on an
otherwise clean account) covering worst-finding aggregation, the
MFA-bypass reasoning, and the root-only key-deletion remediation flow.

---

### 23. networkmanager-core-network-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-networkmanager-core-network`

**What it does:** Audits AWS Network Manager (Cloud WAN) core networks
for detached attachments (active traffic disruption), permissive resource
policies (wildcard or cross-account principals), CIDR overlap across VPC
attachments (silent routing ambiguity), and configuration gaps (LATEST vs
LIVE policy mismatch, orphaned segment references). Emits a deterministic
verdict (DETACHED_ATTACHMENT | PERMISSIVE_POLICY | CIDR_OVERLAP |
CONFIG_GAP | OK) per core network with enumerated findings and specific
CLI remediation.

**When to invoke (trigger phrases):**

- "audit this core network"
- "check Cloud WAN attachment status"
- "CIDR overlap in core network"
- "segment isolation check"
- "core network resource policy"
- "LATEST vs LIVE policy"
- "detached VPC attachment"
- "core network audit"
- "Cloud WAN audit"
- reviewing a core network policy before production deployment or
  opening it to cross-account teams

**Example prompt:**

```
You: "This Cloud WAN core network has a prod VPC and a non-prod VPC
     attached. The prod VPC is 10.0.0.0/16 and the non-prod is
     10.0.1.0/24. Are they safe to open to the shared-services team?"
```

**Expected behavior:**

1. Detects the CIDR overlap (10.0.1.0/24 is inside 10.0.0.0/16) —
   CIDR_OVERLAP verdict. Explains that Cloud WAN silently accepts
   overlapping CIDRs with no creation-time validation.
2. Checks AttachmentStatus (not just State) for every attachment —
   AVAILABLE + ATTACHED passes; AVAILABLE + DETACHED triggers
   DETACHED_ATTACHMENT.
3. Evaluates the resource policy for wildcard or cross-account
   principals without conditions — flags as PERMISSIVE_POLICY.
4. Verifies LATEST policy generation equals LIVE — a mismatch is a
   CONFIG_GAP (changes staged but not deployed).
5. Aggregates to the worst verdict: DETACHED_ATTACHMENT > CIDR_OVERLAP
   > PERMISSIVE_POLICY > CONFIG_GAP > OK.

**End-to-end scenario:** see
[`skills/networkmanager-core-network-auditor/examples/end-to-end.md`](skills/networkmanager-core-network-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (CIDR overlap + cross-account resource
policy) covering severity aggregation, the State-vs-Status distinction,
multi-CIDR VPC advertisement, and CLI remediation.

---

### 26. cost-optimization-hub-recommendations-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cost-optimization-hub`

**What it does:** Audits AWS Cost Optimization Hub configuration for
recommendation enablement, member-account coverage in Organizations,
effort-level distribution, and stale high-value unactioned recommendations.
Emits a deterministic verdict
(DISABLED | NO_MEMBER_ACCOUNTS | HIGH_EFFORT | CONFIG_GAP | OK) per account
with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit cost optimization hub"
- "are cost optimization recommendations enabled"
- "check member account enrollment cost optimization"
- "effort level distribution recommendations"
- "stale high-value recommendations"
- "unactioned cost optimization recommendations"
- "savings estimation mode check"
- "FinOps audit cost optimization hub"

**Example prompt:**

```
You: "Cost Optimization Hub is enrolled but all recommendations are High
     effort and savingsEstimationMode is BEFORE_DISCOUNTS. What's the gap?"
```

**Expected behavior:**

1. Applies the ordered classification (enablement -> member coverage ->
   effort distribution -> config gaps -> OK).
2. Emits VERDICT: HIGH_EFFORT (Step 3 — no Low/Medium effort quick wins
   remain).
3. Identifies the BEFORE_DISCOUNTS savings estimation mode as an additional
   CONFIG_GAP finding (Step 4b).
4. Provides remediation: verify CloudWatch agent deployment, switch to
   AFTER_DISCOUNTS mode, prioritize remaining recommendations by ROI.

**End-to-end scenario:** see
[`skills/cost-optimization-hub-recommendations-auditor/examples/end-to-end.md`](skills/cost-optimization-hub-recommendations-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (stale high-value recs + BEFORE_DISCOUNTS
mode + partial member enrollment) covering multi-finding aggregation, the
savings-overstatement concept, and low-effort-first remediation ordering.

### 23. directconnect-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-directconnect-topology`

**What it does:** Audits AWS Direct Connect topology for hybrid-network
resilience and link-security posture — physical-layer redundancy (2+
connections at **diverse** DX locations, not the same POP — same-location
pairs are pseudo-diversity), MACSec (IEEE 802.1AE) enforcement on capable
dedicated hardware (distinguishing `must_encrypt` from silent-downgrade
`should_encrypt`), BGP MD5 auth on public VIFs (route-hijack defence for
advertised public prefixes), virtual-interface redundancy across diverse
connections via a Direct Connect Gateway (multi-region failover), and
LOA-CFA provisioning state for connections stuck in `requested`. Emits a
deterministic verdict
(SINGLE_CONNECTION | NO_ENCRYPTION | CONFIG_GAP | OK) per topology with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this Direct Connect connection"
- "is my DX redundant"
- "MACSec check Direct Connect"
- "BGP auth public VIF"
- "LOA stuck pending"
- "diverse location Direct Connect"
- "single path failure risk DX"
- "route hijack public VIF"
- "LAG redundancy audit"
- "Direct Connect Gateway failover"
- "should_encrypt vs must_encrypt"
- reviewing a Direct Connect topology before production cutover or a
  compliance audit

**Example prompt:**

```
You: "We just brought up a second Direct Connect connection for
     redundancy. Both terminate at EqSE2. Production hybrid apps depend
     on this link — give me the verdict before we declare cutover."
```

**Expected behavior:**

1. Classifies the topology as SINGLE_CONNECTION (HIGH) — Step 1, the
   worst verdict. Both connections share location EqSE2, so a single
   facility event takes both down. Cites the location-diversity rule
   explicitly.
2. Notes the public VIF without BGP MD5 (CONFIG_GAP, MEDIUM) as a
   secondary finding — route-hijack vector for the advertised prefix.
3. Surfaces MACSec `must_encrypt` on both connections as an OK dimension
   (does not change the verdict; not the worst finding).
4. Provides the correct 4-step remediation: provision a third connection
   at a different DX location (with lead-time caveat: 2-6 weeks),
   re-create the public VIF with `--auth-key` (BGP auth is not
   modifiable in-place), migrate routes via AS-path prepending, and
   optionally add IPsec VPN overlay if procurement is blocked.

**End-to-end scenario:** see
[`skills/directconnect-auditor/examples/end-to-end.md`](skills/directconnect-auditor/examples/end-to-end.md)
for a pre-cutover audit walkthrough (two same-POP connections with a
BGP-auth-less public VIF) covering location-diversity reasoning, the
`bgpAuthKey` write-only gotcha, worst-finding aggregation, and the
destructive VIF re-creation workflow.

---

### 27. budgets-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-budgets`

**What it does:** Audits AWS Budgets for cost-overrun blind spots: accounts
with zero budgets (NO_BUDGET), budgets configured without notifications or
with empty subscriber lists (NO_ALERT — decorative budgets), SNS topic
policies that silently block delivery because they omit the
`budgets.amazonaws.com` publish principal, single-threshold or no-early-
warning alert sets, COST budgets with ACTUAL-only notifications and no
FORECASTED signal, breached or on-track-to-breach actual-vs-forecast spend
with no matching notification, and missing zero-spend guardrails for new or
sandbox accounts. Emits a deterministic verdict
(NO_BUDGET | NO_ALERT | CONFIG_GAP | OK) per account with enumerated findings
and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit my AWS budgets"
- "check budget alerts"
- "is my budget wired to SNS"
- "budget notification threshold"
- "zero-spend budget"
- "cost overrun alert"
- "budget forecast exceeded"
- "spend posture audit"
- "budget SNS policy"
- "decorative budget"
- "budget not alerting"
- "budget alerts not working"
- reviewing cost budgets before a billing review or production cutover

**Example prompt:**

```
You: "We configured a budget but the alerts never arrive. Audit our
     spend posture before the monthly billing review."
```

**Expected behavior:**

1. Classifies the account as CONFIG_GAP — a 100% ACTUAL notification is
   wired to an SNS topic whose policy grants the account root but NOT the
   `budgets.amazonaws.com` service principal (Step 3 — silent delivery
   failure).
2. Notes the single 100% threshold leaves no reaction time (Step 4) and the
   absence of any FORECASTED notification removes the only lead-time signal
   given 8-14h cost-data lag (Step 5).
3. Surfaces the on-track breach: ForecastedSpend > BudgetLimit with no
   FORECASTED notification to fire on it (Step 6).
4. Provides additive remediation: back up the topic policy first, add the
   budgets service principal statement, then add a FORECASTED + an early-
   warning notification, while confirming total notifications stay <= 11.

**End-to-end scenario:** see
[`skills/budgets-auditor/examples/end-to-end.md`](skills/budgets-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (silent SNS delivery failure + single-
threshold + no-forecast + on-track breach) covering the
service-principal-vs-root distinction, cost-data-lag reasoning, and the
additive remediation ordering.

---

### 28. ce-cost-anomaly-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ce-cost-anomaly`

**What it does:** Audits AWS Cost Explorer (CE) anomaly-detection
subscriptions, Savings Plan/RI coverage gaps, idle-resource detection
readiness, and report-subscription cadence. Checks for zero CAD monitors
or zero subscriptions (NO_ANOMALY_SUB — total cost-spike blind spot),
steady-state eligible compute spend (>$1k/mo) with RI coverage < 40% AND
SP coverage < 40% (LOW_RI_COVERAGE — on-demand leak), and configuration
quality gaps: an IMMEDIATE monitor paired with a WEEKLY subscription
(notification latency >> detection latency), the $100 default threshold
on a free-tier or low-spend account, DAILY-only monitors with no
IMMEDIATE on accounts > $5k/mo, no CUR v2 with resource IDs (idle-
resource detection impossible via CE), and narrow monitor scope with no
org/linked-account breadth. Emits a deterministic verdict
(NO_ANOMALY_SUB | LOW_RI_COVERAGE | CONFIG_GAP | OK) per account with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit Cost Anomaly Detection"
- "check my anomaly subscription"
- "is CAD wired correctly"
- "RI coverage gap"
- "Savings Plan coverage"
- "anomaly threshold too high"
- "idle resource detection"
- "IMMEDIATE vs DAILY monitor"
- "cost spike alerting"
- "commitment gap"
- "on-demand leak"
- reviewing CE/CAD configuration before a billing review or quarterly
  FinOps assessment

**Example prompt:**

```
You: "Review our Cost Explorer and Cost Anomaly Detection setup before
     the quarterly billing review. We spend about $20k/month on
     steady-state EC2 and want to make sure we're not leaking on-demand
     spend or missing cost spikes."
```

**Expected behavior:**

1. Classifies the account as LOW_RI_COVERAGE — $18k/mo eligible EC2
   spend with 22% RI / 12% SP coverage (Step 2 — commitment strategy
   absent or undersized on a steady-state fleet).
2. Notes the IMMEDIATE monitor is paired with a WEEKLY subscription
   (Step 3a — the monitor detects in ~5 min but the subscription
   delivers a digest 7 days later; the operator sees the spike a week
   late).
3. Flags the $100 default threshold as miscalibrated for a $20k/mo
   account (Step 3b — recommended ~$1000-$2000, i.e. 5-10% of monthly
   spend).
4. Distinguishes coverage (USAGE offset by commitment — the leak to
   close) from utilization (COMMITMENT consumed — over-buy waste). The
   LOW_RI_COVERAGE verdict means "run a commitment analysis," not "buy
   RIs today."

**End-to-end scenario:** see
[`skills/ce-cost-anomaly-auditor/examples/end-to-end.md`](skills/ce-cost-anomaly-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (frequency mismatch + threshold
miscalibration + low coverage) covering the frequency-vs-detection-
cadence distinction, the coverage-vs-utilization distinction, and the
additive remediation ordering.

---

### 29. dynamodb-table-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-dynamodb-table`

**What it does:** Audits DynamoDB table configurations for encryption-at-rest
(KMS — customer-managed CMK vs AWS-managed vs default AES256), point-in-time
recovery (PITR), capacity mode (on-demand vs provisioned with autoscaling,
including GSI cascade-throttle detection), TTL configuration, backup posture,
GSI/LSI quota risk, and deletion protection. Emits a deterministic verdict
(UNENCRYPTED | NO_PITR | CAPACITY_MISMATCH | CONFIG_GAP | OK) per table with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this DynamoDB table"
- "is my DynamoDB table encrypted"
- "check PITR on DynamoDB"
- "DynamoDB capacity mode"
- "DynamoDB backup posture"
- "is deletion protection enabled"
- "GSI quota DynamoDB"
- "DynamoDB autoscaling missing"
- "harden DynamoDB table"
- "DynamoDB compliance audit"
- reviewing a DynamoDB table before production deployment or SOC2/PCI review

**Example prompt:**

```
You: "This DynamoDB table has SSE disabled, PITR off, and no autoscaling.
     Production cutover is tomorrow — what's the verdict and remediation?"
```

**Expected behavior:**

1. Applies the ordered classification (encryption → PITR → capacity → config).
2. Emits VERDICT: UNENCRYPTED (Step 1 — worst finding wins; SSE disabled means
   no customer-controlled KMS encryption).
3. Enumerates NO_PITR and any CONFIG_GAP findings as additional line items.
4. Provides ordered CLI remediation: enable SSE-KMS with customer CMK, enable
   PITR, set up autoscaling or switch to on-demand, enable deletion protection.

**End-to-end scenario:** see
[`skills/dynamodb-table-auditor/examples/end-to-end.md`](skills/dynamodb-table-auditor/examples/end-to-end.md)
for a production-readiness audit walkthrough (SSE disabled + PITR disabled +
no deletion protection) covering worst-first aggregation, the
"UNENCRYPTED does not mean plaintext" concept, and the per-finding CLI
remediation workflow.

---

### 35. trustedadvisor-check-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-trustedadvisor-checks`

**What it does:** Audits AWS Trusted Advisor check results across all five
pillars (Cost Optimization, Performance, Security, Fault Tolerance, Service
Limits) for actionable findings, recommended actions, and structural gaps
that undermine trust in TA data. Checks for support-tier gating
(Basic/Developer exposes ~7 of ~115 checks — CONFIG_GAP for limited
coverage), stale check results (timestamp > 24 hours renders an `ok` status
unreliable), `not_available` status (check could not evaluate — different
from `ok`), excluded resources (permanently hidden findings that persist
across refreshes), and graduated service-limits severity (>= 100% =
CRITICAL, 80-99% = WARNING). Applies a category-severity matrix: Security
and Fault Tolerance errors are CRITICAL_CHECK, Cost Optimization and
Performance errors are WARNING_CHECK. Emits a deterministic verdict
(CRITICAL_CHECK | WARNING_CHECK | CONFIG_GAP | OK) per check with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit Trusted Advisor checks"
- "review TA findings"
- "is TA configured correctly"
- "check support tier coverage"
- "stale Trusted Advisor results"
- "excluded TA resources"
- "not_available TA check"
- "service limit exceeded"
- "cost optimization findings"
- "fault tolerance findings"
- "Basic support limited checks"
- "compliance review Trusted Advisor"
- reviewing TA check results before a compliance or operational review

**Example prompt:**

```
You: "Review these Trusted Advisor check results before the compliance
     audit. One of them might be stale — I grabbed the export 3 days ago."
```

**Expected behavior:**

1. Classifies the security check with `error` status (open RDP port 3389
   to 0.0.0.0/0) as CRITICAL_CHECK — Step 2, Security pillar errors are
   always CRITICAL.
2. Classifies the cost check with `error` status (idle EBS volume) as
   WARNING_CHECK — Step 2, Cost Optimization errors are WARNING, never
   CRITICAL (cost waste does not cause breaches).
3. Catches the stale result (4-day-old timestamp on the CloudTrail check)
   as CONFIG_GAP — Step 1, an `ok` status from 96 hours ago is not
   trustworthy for a compliance audit.
4. Distinguishes between category severities explicitly so the operator
   triages the security exposure before the cost waste.

**End-to-end scenario:** see
[`skills/trustedadvisor-check-auditor/examples/end-to-end.md`](skills/trustedadvisor-check-auditor/examples/end-to-end.md)
for a multi-check walkthrough (security error + cost error + stale ok)
covering the category-severity matrix, staleness-as-CONFIG_GAP reasoning,
and per-finding CLI remediation ordering.

---

### 30. rds-instance-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-rds-instance`

**What it does:** Audits AWS RDS DB instances across the seven high-impact
configuration dimensions that drive data-loss and outage incidents — public
accessibility (`PubliclyAccessible: true` is an internet-exposed database and
the worst-impact RDS misconfiguration), encryption-at-rest (immutable after
creation — remediation is a snapshot migration, not a toggle), deletion
protection (single API call can destroy the instance), Multi-AZ availability
(standby failover for AZ resilience), automated-backup / PITR retention
(`0` disables point-in-time recovery entirely), auto minor-version upgrade
(patching hygiene during the maintenance window), and Enhanced Monitoring
(OS-level metrics). Defers Aurora engines to the DBCluster block for
encryption/deletion/Multi-AZ/retention — those are cluster-level properties.
Emits a deterministic verdict
(PUBLIC | UNENCRYPTED | NO_DELETION_PROTECTION | SINGLE_AZ | CONFIG_GAP | OK)
per instance with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this RDS instance"
- "is my database public"
- "check RDS encryption"
- "is deletion protection enabled"
- "are automated backups on"
- "Multi-AZ check"
- "minor version upgrade"
- "Enhanced Monitoring off"
- "harden RDS instance"
- "PubliclyAccessible true"
- "BackupRetentionPeriod zero"
- reviewing an RDS instance before production deployment or a compliance audit

**Example prompt:**

```
You: "We inherited this MySQL instance from a team that left in a hurry.
     PubliclyAccessible is true and StorageEncrypted is false. Give me the
     verdict and the remediation plan before we onboard payments to it."
```

**Verdict shape:** `PUBLIC | UNENCRYPTED | NO_DELETION_PROTECTION | SINGLE_AZ | CONFIG_GAP | OK`

**End-to-end scenario:** see
[`skills/rds-instance-auditor/examples/end-to-end.md`](skills/rds-instance-auditor/examples/end-to-end.md)
for a public-and-unencrypted audit walkthrough covering severity aggregation
(PUBLIC worst, UNENCRYPTED secondary), the immutability-of-encryption concept
(snapshot migration, not `modify-db-instance`), and the per-finding CLI
remediation workflow.


### 36. controltower-control-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-controltower-controls` — or route via `/aws:pipeline`.

**What it does:** Audits AWS Control Tower landing-zone state, enabled
controls (preventive, detective, proactive), guardrail enforcement
integrity, and account-factory baseline health. Cross-references the
underlying enforcement mechanism (SCP content, Config Rule existence,
CloudFormation hook presence, execution role, Config recorder) against the
Control Tower registry state — because a control showing ENABLED does not
mean it is enforcing. Emits a deterministic verdict
(DRIFT | DISABLED_CONTROL | CONFIG_GAP | OK) per OU or landing zone with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit control tower"
- "check landing zone drift"
- "control tower guardrails"
- "enabled controls status"
- "control drift detection"
- "account factory baseline"
- "mandatory controls disabled"
- "SCP drift control tower"
- "config recorder gap"
- "AWSControlTowerExecutionRole missing"
- "landing zone upgrade check"
- reviewing Control Tower posture before a governance or compliance review

**Example prompt:**

```
You: "This preventive control shows SUCCEEDED in Control Tower but the SCP
     verification shows the Deny on port 22 was removed. What is the real
     enforcement posture?"
```

**Expected behavior:**

1. Applies the 7-step classification in dependency order (landing-zone drift
   -> control-level drift -> mandatory control enforcement -> Config health
   -> execution role -> account factory baseline -> aggregation).
2. Emits VERDICT: DRIFT (Step 2 — SCP content mismatch, enforcement broken
   while control shows SUCCEEDED).
3. Cites the root cause: SCP was modified outside Control Tower via
   organizations:UpdatePolicy; the control registry has not detected the
   drift yet.
4. Provides specific remediation: disable/re-enable control to re-deploy
   canonical SCP, audit CloudTrail for the modification event.

**Verdict shape:** `DRIFT | DISABLED_CONTROL | CONFIG_GAP | OK`

**End-to-end scenario:** see
[`skills/controltower-control-auditor/examples/end-to-end.md`](skills/controltower-control-auditor/examples/end-to-end.md)
for a multi-finding audit walkthrough (SCP drift + Config recorder gap +
execution role missing) covering severity aggregation, the silent-
enforcement-break concept, and the disable/re-enable remediation workflow.


---

### 29. auditmanager-assessment-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-auditmanager-assessment`

**What it does:** Audits AWS Audit Manager assessments for evidence-
collection integrity, control compliance rate, delegation wiring, and
account-level settings posture. Evaluates assessment lifecycle state
(ACTIVE vs stopped/INACTIVE), the data-source dependency chain (AWS Config
recording + CloudTrail management-event logging), NOT_ASSESSED burden,
FAIL burden, framework scope coverage, KMS-key/SNS-topic/reports-
destination/process-owner configuration, and outstanding delegations.
Emits a deterministic verdict (INCOMPLETE_EVIDENCE | LOW_COMPLIANCE |
CONFIG_GAP | OK) per assessment with enumerated findings and CLI
remediation.

**When to invoke (trigger phrases):**

- "audit this Audit Manager assessment"
- "is my assessment evidence complete"
- "is the compliance score trustworthy"
- "stopped assessment — stale evidence"
- "NOT_ASSESSED controls — data-source problem"
- "Audit Manager settings gap"
- "assessment delegation pending"
- "compliance report readiness"
- reviewing an Audit Manager assessment before generating a compliance
  report

**Example prompt:**

```
You: "This SOC 2 assessment shows 31% compliance and status INACTIVE.
     Is this number trustworthy enough to put in the compliance report?"
```

**Expected behavior:**

1. Classifies the assessment as INCOMPLETE_EVIDENCE — status INACTIVE
   since 2026-02-14 (Step 1a, frozen score), and 42% of controls are
   NOT_ASSESSED with Config recorder OFF in account 222222222222
   (Step 1b, data-source break).
2. Distinguishes evidence-integrity from compliance: the 31% compliance
   is driven by NOT_ASSESSED (collection gap), not by FAIL (control
   failure). The correct remediation is to repair Config + reactivate
   the assessment, not to chase failing controls.
3. Provides the data-source-repair remediation chain: repair Config,
   reactivate, wait one collection cycle (~24h), re-baseline the
   compliance %, then generate the report.

**End-to-end scenario:** see
[`skills/auditmanager-assessment-auditor/examples/end-to-end.md`](skills/auditmanager-assessment-auditor/examples/end-to-end.md)
for a stopped-assessment walkthrough covering the evidence-integrity-over-
compliance-number principle, the frozen-dashboard trap, and the
data-source-repair remediation workflow.

---

### 37. organizations-scp-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-organizations-scp`

**What it does:** Audits AWS Organizations Service Control Policies (SCPs)
for effective permission boundaries across the OU hierarchy. Evaluates
FullAWSAccess inheritance (deny-list vs allow-list mode), deny-list
guardrails (organizations:LeaveOrganization, security-service disruption,
region restriction via aws:RequestedRegion), account-level overrides,
and silently ineffective Deny statements using unsupported service-specific
condition keys (kms:ViaService, s3:prefix, ec2:ResourceTag). Emits a
deterministic verdict (PERMISSIVE_SCP | MISSING_GUARDRAIL | CONFIG_GAP |
OK) per target with enumerated findings and specific remediation.

**When to invoke (trigger phrases):**

- "audit these SCPs"
- "check SCP guardrails"
- "effective permissions for this OU"
- "is LeaveOrganization denied?"
- "FullAWSAccess strategy"
- "SCP deny-list review"
- "OU hierarchy security"
- "organization guardrail audit"
- reviewing SCPs before attaching to production OUs

**Example prompt:**

```
You: "We just restructured our OU hierarchy and I'm seeing AccessDenied
     everywhere. Here are our SCPs — root has FullAWSAccess detached
     and a region lock. What's wrong?"
```

**Expected behavior:**

1. Classifies the structural issue (FullAWSAccess detached with no Allow
   replacement = CONFIG_GAP, Step 1a).
2. Identifies that the region-restriction SCP uses a supported condition
   key (aws:RequestedRegion) and would work once the Allow gap is fixed.
3. Emits VERDICT: CONFIG_GAP with enumerated findings and re-attach
   remediation (with operator-confirmation gate).

**End-to-end scenario:** see
[`skills/organizations-scp-auditor/examples/end-to-end.md`](skills/organizations-scp-auditor/examples/end-to-end.md)
for a full OU-hierarchy audit walkthrough covering FullAWSAccess
mode-switch mechanics, Deny absolutism across the inheritance chain,
unsupported condition-key detection, and the additive-Deny-SCP
remediation workflow.

---

### codecommit-repository-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-codecommit-repository`

**What it does:** Audits AWS CodeCommit repositories for approval-rule
coverage, customer-managed KMS encryption, default-branch deletion
protection (IAM enforced, not native), notification-rule alerting, and the
CodeCommit service-wide deprecation/maintenance risk.

**When to invoke (trigger phrases):**

- "audit this CodeCommit repository"
- "check CodeCommit approval rules"
- "is my CodeCommit repo encrypted?"
- "CodeCommit branch protection"
- "CodeCommit notification rules"
- "CodeCommit deprecation"
- "should we migrate off CodeCommit?"

**Example prompt:**

```
You: /aws:audit-codecommit-repository

     "Audit this repo:
     Repository name: my-app-backend
     defaultBranch: main
     kmsEncryptionKeyId: aws/codecommit
     approvalRuleTemplates: []
     notificationRules: []
     branchProtectionIamPolicies: []
     tags: {}"
```

**Expected behavior:**

1. Emits VERDICT: NO_APPROVAL_RULE (no template linked — worst finding).
2. Notes NO_ENCRYPTION (AWS-managed key) and CONFIG_GAP (no notifications,
   no branch protection) as secondary findings.
3. Always includes DEPRECATION_RISK finding (CodeCommit is deprecated).
4. Remediation: create approval rule template, plan CMK migration, add IAM
   branch protection, create CodeStar notification rules, evaluate migration.

---

### sqs-dlq-policy-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-sqs-dlq-policy`

**What it does:** Audits AWS SQS queues for dead-letter-queue (DLQ)
configuration gaps, public access via `Principal: "*"` queue policies,
encryption-at-rest status (SSE-SQS / SSE-KMS), `maxReceiveCount` tuning,
message-retention periods, and cross-account DLQ accessibility. Emits a
deterministic verdict (NO_DLQ | PUBLIC_ACCESS | NO_ENCRYPTION | CONFIG_GAP |
OK) per queue with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this SQS queue"
- "is my SQS queue missing a DLQ"
- "check SQS redrive policy"
- "is my SQS queue public"
- "SQS queue encryption"
- "maxReceiveCount tuning"
- "DLQ retention period"
- "cross-account DLQ"
- "poison pill SQS"
- "harden SQS queue"
- reviewing an SQS queue before production deployment or compliance audit

**Example prompt:**

```
You: "This SQS queue has Principal:* in the policy and no DLQ configured.
     Production cutover is tomorrow — what's the verdict and remediation?"
```

**Expected behavior:**

1. Applies the ordered classification (public access → DLQ → encryption →
   config gaps → OK).
2. Emits VERDICT: PUBLIC_ACCESS (Step 1 — worst finding wins; the wildcard
   principal with no condition is CRITICAL).
3. Enumerates NO_DLQ as an additional HIGH finding (Step 2).
4. Provides ordered CLI remediation: add aws:SourceArn condition or
   remove wildcard principal, create and attach DLQ, enable SSE-SQS,
   tune maxReceiveCount, set DLQ retention to 14 days.

**Key distinction the skill makes:** `Principal: "*"` with an
`aws:SourceArn` condition (the standard S3-event-notification or
SNS-subscription pattern) is SAFE — the condition restricts access to the
specific source resource. Only `Principal: "*"` with NO strong condition
is classified as PUBLIC_ACCESS.

**End-to-end scenario:** see
[`skills/sqs-dlq-policy-auditor/examples/end-to-end.md`](skills/sqs-dlq-policy-auditor/examples/end-to-end.md)
for a holiday-traffic audit walkthrough (public access via legacy wildcard
statement + safe S3-notification statement + DLQ retention gap) covering
the Principal:"*" SourceArn distinction, severity aggregation, and the
assume-breach remediation workflow.

---

### eventbridge-bus-policy-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-eventbridge-bus-policy`

**What it does:** Audits AWS EventBridge event buses for public
event-injection exposure (`Principal: "*"` or cross-account with
`events:PutEvents` and no strong condition), missing dead-letter queues
on rule targets, absent customer-managed KMS encryption
(`KmsKeyIdentifier`), and archive/enrichment gaps. Emits a deterministic
verdict (PUBLIC_BUS | NO_DLQ | NO_ENCRYPTION | CONFIG_GAP | OK) per bus
with enumerated findings and specific remediation.

**When to invoke (trigger phrases):**

- "audit this event bridge bus"
- "is my event bus public"
- "check eventbridge bus policy"
- "event injection risk"
- "missing DLQ on rule"
- "is event bridge encrypted"
- "event bus cross-account"
- "Principal star eventbridge"
- "dead-letter queue check"
- "event bridge archive gap"
- reviewing an EventBridge bus before production deployment

**Example prompt:**

```
You: "This event bus grants events:PutEvents to Principal {AWS: *} with
     no condition. The rule targets don't have DLQs. What's the risk?"
```

**Expected behavior:**

1. Classifies the principal scope (wildcard), action danger (INJECT —
   PutEvents is an event-injection blast-radius multiplier), and
   condition strength (none).
2. Emits VERDICT: PUBLIC_BUS (Step 5a — wildcard PutEvents, no
   condition).
3. Identifies the DLQ gap as an additional NO_DLQ finding.
4. Provides assume-breach remediation: scope the principal, add
   conditions, attach DLQs, associate CMK, create archive.

**End-to-end scenario:** see
[`skills/eventbridge-bus-policy-auditor/examples/end-to-end.md`](skills/eventbridge-bus-policy-auditor/examples/end-to-end.md)
for a multi-finding audit walkthrough (wildcard PutEvents + missing
per-target DLQs + absent CMK) covering event-injection reasoning, the
root-delegation exception, per-target DeadLetterConfig semantics, and
severity aggregation.

### codepipeline-pipeline-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-codepipeline-pipeline`

**What it does:** Audits AWS CodePipeline pipelines for artifact-store
encryption (KMS CMK presence), cross-account or over-permissive action
roles, disabled stage transitions, source-action credential posture
(GitHub v1 OAuth vs CodeStar Connection), and manual-approval gate
coverage.

**When to invoke (trigger phrases):**

- "audit this CodePipeline pipeline"
- "is my pipeline artifact store encrypted?"
- "check for disabled stage transitions"
- "cross-account deploy role in pipeline"
- "GitHub v1 source deprecated"
- "missing manual approval gate"
- "over-permissive pipeline role"
- "CodeStar Connection check"

**Example prompt:**

```
You: /aws:audit-codepipeline-pipeline

     "Audit this pipeline:
     Pipeline name: prod-deploy-pipeline
     artifactStore: { type: S3, location: my-bucket } (no encryptionKey)
     Source: ThirdParty/GitHub (v1 OAuth)
     Deploy: CloudFormation, RoleArn: arn:aws:iam::111111111111:role/Deploy
     Pipeline state: all transitions enabled
     Artifact bucket SSE: none"
```

**Expected behavior:**

1. Emits VERDICT: NO_ENCRYPTION (artifact store has no CMK — worst finding).
2. Notes CONFIG_GAP (GitHub v1 deprecated source) as secondary finding.
3. Remediation: create CMK, grant pipeline role KMS permissions, migrate
   to CodeStar Connection, update pipeline definition.

**End-to-end scenario:** see
[`skills/codepipeline-pipeline-auditor/examples/end-to-end.md`](skills/codepipeline-pipeline-auditor/examples/end-to-end.md)
for a full production pipeline audit walkthrough covering artifact
encryption gaps, deprecated source credential migration, missing approval
gates, and the worst-finding aggregation logic.

---

### sns-topic-public-subscription-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-sns-topic-public-subscription`

**What it does:** Audits SNS topics for public subscription exposure
(Principal:"*" with sns:Subscribe/Publish in topic policy), missing KMS
encryption, delivery-status logging gaps, FIFO deduplication
misconfiguration, and cross-account subscriptions.

**When to invoke (trigger phrases):**

- "audit this SNS topic"
- "is my SNS topic public?"
- "SNS public subscription"
- "who can subscribe to my topic?"
- "SNS delivery logging"
- "SNS FIFO deduplication"
- "harden SNS topic policy"
- reviewing an SNS topic before production deployment

**Example prompt:**

```
You: "This SNS topic has Principal:* with sns:Subscribe in the policy and
     no KMS encryption. What's the exposure?"
```

**Expected behavior:**

1. Applies the ordered classification (public subscription → KMS encryption
   → delivery logging → FIFO dedup → cross-account subs → aggregation).
2. Emits VERDICT: PUBLIC_SUBSCRIPTION (Step 1 — Principal:"*" with
   sns:Subscribe and no condition is push-based data exfiltration).
3. Identifies NO_ENCRYPTION as an additional finding (Step 2).
4. Provides assume-breach remediation: scope the principal, add
   aws:SourceOwner condition, enable CMK encryption, configure delivery
   logging.

**Key distinction the skill makes:** `sns:Subscribe` with `Principal: "*"`
is worse than the equivalent SQS public-read — SNS pushes messages to the
subscriber automatically (no polling required), making it a passive,
persistent data exfiltration pipe. `Principal: "*"` with `aws:SourceOwner`
condition is downgraded to CONFIG_GAP (scoped but fragile).

**End-to-end scenario:** see
[`skills/sns-topic-public-subscription-auditor/examples/end-to-end.md`](skills/sns-topic-public-subscription-auditor/examples/end-to-end.md)
for a multi-finding audit walkthrough (public Subscribe + no encryption +
FIFO dedup off) covering push-exfiltration reasoning, the
aws:SourceOwner downgrade, per-protocol delivery logging, and severity
aggregation.

---

### stepfunctions-statemachine-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-stepfunctions-statemachine`

**What it does:** Audits Step Functions state machines across four
orthogonal dimensions — execution logging coverage (`level: ALL` +
`includeExecutionData: true`), X-Ray tracing enablement (including the
Express-workflow no-op trap where `TracingConfiguration.enabled: true`
silently produces no X-Ray traces), execution-role blast radius
(`Action "*"` on `Resource "*"`, service wildcards,
`states:StartExecution` chaining, `iam:PassRole`), and ASL definition
validation (fallible Tasks without Catch/Retry, missing `TimeoutSeconds`,
unreachable states, cyclic references without exit, Choice without
Default). Emits a deterministic verdict
(`NO_LOGGING | NO_TRACING | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK`) per
state machine with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this state machine"
- "check Step Functions logging"
- "is X-Ray tracing enabled?"
- "is the execution role too broad?"
- "validate this ASL definition"
- "does this Task have error handling?"
- "is this Express workflow traced?"
- reviewing a state machine before production promotion

**Example prompt:**

```
You: "This Standard workflow has logging level ALL but
     includeExecutionData false. The role grants lambda:* on *. Is this
     production-ready?"
```

**Expected behavior:**

1. Classifies the execution role as OVERPERMISSIVE_ROLE (lambda wildcard
   on `*` — fan-out access to every Lambda function in the account).
2. Flags the `includeExecutionData: false` trap as NO_LOGGING — state
   transitions are logged but NOT input/output payloads (forensically
   near-useless).
3. Aggregates by precedence: OVERPERMISSIVE_ROLE > NO_LOGGING, so the
   verdict is OVERPERMISSIVE_ROLE with the logging gap in FINDINGS.
4. Emits specific CLI remediation: scope the role to named actions on
   specific ARNs, and `update-state-machine` with
   `includeExecutionData=true`.

**End-to-end scenario:** see
[`skills/stepfunctions-statemachine-auditor/examples/end-to-end.md`](skills/stepfunctions-statemachine-auditor/examples/end-to-end.md)
for a multi-finding audit walkthrough (over-permissive role +
includeExecutionData trap on an order pipeline) covering precedence
aggregation, the fan-out blast-radius concept, and the role-scoping +
logging-fix remediation workflow.

---

### sagemaker-endpoint-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-sagemaker-endpoint`

**What it does:** Audits SageMaker real-time and async endpoints across six
orthogonal dimensions — VPC configuration (the VpcConfig-on-Model knowledge
delta — the most common audit mistake is checking the EndpointConfig instead
of the Model), KMS encryption at rest and inter-container traffic encryption
(only relevant for multi-container inference pipelines), execution-role
blast radius (`Action "*"` on `Resource "*"`, service wildcards, PassRole
on `"*"`), data capture and model monitoring schedule coverage (both must
be present — capture alone provides no alerts, a schedule alone has no
data), and instance count for high availability (`InitialInstanceCount < 2`
= no HA). Emits a deterministic verdict
(`NO_ENCRYPTION | OVERPERMISSIVE_ROLE | NO_MONITORING | PUBLIC_ENDPOINT |
CONFIG_GAP | OK`) per endpoint with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit this SageMaker endpoint"
- "is my endpoint encrypted?"
- "is the endpoint in a VPC?"
- "is the execution role too broad?"
- "is model monitoring enabled?"
- "is this endpoint production-ready?"
- "inter-container encryption"
- reviewing a SageMaker endpoint before production deployment

**Example prompt:**

```
You: "This SageMaker endpoint has no VpcConfig on the Model, the execution
     role grants sagemaker:* on *, and there's no monitoring schedule.
     Is it production-ready?"
```

**Expected behavior:**

1. Classifies the Model as PUBLIC_ENDPOINT (no VpcConfig — endpoint is
   internet-facing; VpcConfig lives on the Model, NOT the EndpointConfig).
2. Identifies the execution role as OVERPERMISSIVE_ROLE (`sagemaker:*` on
   `"*"` — the container only needs InvokeEndpoint, not model management).
3. Flags the absent monitoring as NO_MONITORING (no DataCaptureConfig AND
   no MonitoringSchedule — drift undetectable).
4. Aggregates by precedence: PUBLIC_ENDPOINT > OVERPERMISSIVE_ROLE >
   NO_MONITORING, so the verdict is PUBLIC_ENDPOINT with all three findings
   in FINDINGS.
5. Emits the blue/green remediation workflow: create-model with VpcConfig,
   new EndpointConfig with DataCaptureConfig, update-endpoint, scope the
   execution role to named actions on specific ARNs.

**End-to-end scenario:** see
[`skills/sagemaker-endpoint-auditor/examples/end-to-end.md`](skills/sagemaker-endpoint-auditor/examples/end-to-end.md)
for a multi-finding audit walkthrough (public endpoint + no monitoring on a
fraud-detection model) covering precedence aggregation, the VpcConfig-on-Model
knowledge delta, and the immutable-resource blue/green remediation workflow.

---

### dms-replication-task-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-dms-replication-task`

**What it does:** Audits DMS replication tasks across five dimensions —
TLS/SSL on source and target endpoints (`SslMode: none` or missing = NO_TLS;
`require` = CONFIG_GAP with no cert verification; `verify-ca`/`verify-full`
= OK), task logging (`EnableLogging: false` or absent = NO_LOGGING — the
metrics-vs-logs trap where CloudWatch metrics stay green while data is
silently lost), replication instance config (`PubliclyAccessible: true`,
single-AZ on CDC tasks, burstable instance class), endpoint encryption
(missing `KmsKeyId`), and task settings integrity (validation, recovery
table, deletion protection). Emits a deterministic verdict
(`NO_TLS | NO_LOGGING | CONFIG_GAP | OK`) per task with priority-based
aggregation (first failing dimension wins) and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this DMS replication task"
- "check DMS endpoint SSL"
- "is my DMS migration encrypted"
- "DMS CDC logging"
- "replication instance public"
- "hardening DMS migration"
- reviewing a replication task before production cutover

**Example prompt:**

```
You: "This CDC task has source SslMode none and the replication
     instance is PubliclyAccessible true. Is this production-ready?"
```

**Expected behavior:**

1. Classifies the source endpoint as NO_TLS — plaintext data pipe between
   source and target databases.
2. Flags the replication instance PubliclyAccessible as CONFIG_GAP —
   internet-reachable credential store.
3. Aggregates by priority: NO_TLS > CONFIG_GAP, so the verdict is NO_TLS
   with the instance exposure in FINDINGS.
4. Emits specific CLI remediation: stop the task, modify endpoint SslMode
   to verify-full, make the instance private.

**End-to-end scenario:** see
[`skills/dms-replication-task-auditor/examples/end-to-end.md`](skills/dms-replication-task-auditor/examples/end-to-end.md)
for a multi-finding audit walkthrough (plaintext endpoint + public instance
+ disabled logging on a production MySQL-to-PostgreSQL migration) covering
priority aggregation, the metrics-vs-logs trap, and the stop-modify-restart
remediation workflow.

---

### ssm-managed-instance-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-ssm-managed-instance`

**What it does:** Audits AWS Systems Manager (SSM) managed instances
across six dimensions — instance coverage (SSM Agent reachable + IAM
profile attached), association compliance, patch baseline adherence,
Session Manager vs SSH exposure, inventory collection, and Run Command
posture. Emits a deterministic verdict
(UNMANAGED | NONCOMPLIANT | NO_SESSION_MANAGER | CONFIG_GAP | OK) per
instance with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit my SSM managed instances"
- "why is this instance ConnectionLost"
- "is Session Manager enabled?"
- "patch compliance status"
- "is inventory collection enabled?"
- "AWS-ApplyPatchBaseline failed"
- "open SSH instead of Session Manager"
- "audit hybrid activation instances"
- "mi- instance coverage"
- "AmazonSSMManagedInstanceCore"

**Example prompt:**

```
You: "My EC2 instance i-0abc123 has no IAM profile — describe-instance-information
     returns nothing. Patch state and Session Manager data are absent. What's
     the verdict?"
```

**Expected behavior:**

1. Classifies the instance as UNMANAGED (Rule C-1 — no IAM instance
   profile, SSM Agent cannot authenticate).
2. Stops at the coverage finding — does NOT evaluate patch/session/
   inventory on a non-reporting instance (downstream data is noise).
3. Provides specific remediation: attach a role with
   `AmazonSSMManagedInstanceCore`, wait 5-10 min for agent registration,
   re-audit.

**End-to-end scenario:** see
[`skills/ssm-managed-instance-auditor/examples/end-to-end.md`](skills/ssm-managed-instance-auditor/examples/end-to-end.md)
for a four-instance fleet walkthrough (UNMANAGED + NONCOMPLIANT +
NO_SESSION_MANAGER + OK) covering the silent coverage gap (EC2 with no
profile, invisible to describe-instance-information), the
Success-vs-NON_COMPLIANT patch distinction, and the SSH-as-parallel-
weaker-control framing.

---

### cloudwatch-logs-retention-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cloudwatch-logs-retention`

**What it does:** Audits CloudWatch Logs log groups for Never-expire
retention (silent infinite-cost accumulation), missing SSE-KMS
customer-managed-key (CMK) encryption, retention × volume cost risk,
subscription filter fan-out (Lambda/Kinesis/cross-account destination),
missing metric filters, and absent CloudWatch Logs Anomaly Detectors.
Emits a deterministic first-fail-wins verdict
(NO_RETENTION | NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK) per log
group with enumerated findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit this CloudWatch Logs group"
- "is my log group retention set"
- "Never expire log group"
- "check CloudWatch Logs cost"
- "is CloudWatch Logs encrypted with KMS"
- "are metric filters configured"
- "is anomaly detection enabled"
- "subscription filter audit"
- "CloudWatch Logs compliance check"
- "log group cost risk"
- reviewing a log group before compliance review

**Example prompt:**

```
You: "This log group has retentionInDays absent, kmsKeyId set, and a
     Lambda subscription filter with empty pattern. storedBytes is 500 GB.
     What's the risk and the fix?"
```

**Expected behavior:**

1. Validates retention field absence (Never expire) — Step 1 fires
   NO_RETENTION (CRITICAL) via first-fail-wins.
2. If retention is set, validates CMK presence — Step 2 may fire
   NO_ENCRYPTION (HIGH).
3. If both pass, evaluates retention × storedBytes against cost
   thresholds — Step 3 may fire COST_RISK (HIGH).
4. If all prior dimensions pass, checks metric filter + anomaly
   detector coverage — Step 4 may fire CONFIG_GAP (MEDIUM).
5. Emits VERDICT + REASON + FINDINGS + REMEDIATION with specific CLI
   per finding (PutRetentionPolicy, AssociateKmsKey with key-policy
   snippet, PutMetricFilter, PutAnomalyDetector).

**End-to-end scenario:** see
[`skills/cloudwatch-logs-retention-auditor/examples/end-to-end.md`](skills/cloudwatch-logs-retention-auditor/examples/end-to-end.md)
for a `/prod/checkout-api` walkthrough (3650-day retention × 512 GB
with CMK + Lambda subscription filter) covering first-fail-wins
ordering, the `storedBytes` vs current-storage distinction, the
Lambda-fan-out cost multiplier, and the legacy-events retention caveat.

---

## /aws:audit-service-quotas-usage

**Slash command:** `/aws:audit-service-quotas-usage` — or route via `/aws:pipeline`.

Audit AWS Service Quotas for utilization risk, alarm coverage, and
quota-increase-request health. Reads a Service Quotas snapshot (applied
value, default value, UsageMetric, utilization, increase request history,
CloudWatch alarm state) and applies ordered classification:

1. **APPROACHING_LIMIT** — utilization >= 80% of applied quota. The
   operational risk of imminent exhaustion dominates all other findings.
   A PENDING increase request has NOT taken effect — the applied value
   is still the old number until APPROVED.
2. **CONFIG_GAP** — structural issues: no UsageMetric (cannot auto-monitor
   via CloudWatch), Adjustable: false at high utilization, DENIED increase
   request with utilization >= 50%, or adjustable quota stuck at default
   with >= 50% utilization and no increase request.
3. **NO_ALARM** — quota has UsageMetric, utilization < 80%, but no
   CloudWatch alarm configured on the AWS/Usage metric.
4. **OK** — utilization low, alarm in place (or N/A), no structural issues.

Key expert distinctions: `list-service-quotas` returns the APPLIED value
(not the AWS default — use `get-aws-default-service-quota` for that);
only quotas with a `UsageMetric` block emit `AWS/Usage` CloudWatch metrics;
regional quotas (GlobalQuota: false) must be increased per-region; and
`QuotaCode` (e.g., L-1212C26A) is the stable identifier (not QuotaName).

**Expected behavior:**

1. Classifies utilization >= 80% as APPROACHING_LIMIT regardless of alarm
   state or pending requests — the applied quota has not changed yet.
2. Flags quotas without UsageMetric as CONFIG_GAP — there is no CloudWatch
   metric to alarm on, so the quota cannot be auto-monitored.
3. Flags DENIED increase requests at >= 50% utilization as CONFIG_GAP — the
   increase path was blocked and no alternative plan exists.
4. Emits VERDICT + REASON + UTILIZATION + FINDINGS + REMEDIATION with
   specific CLI (request-service-quota-increase, put-metric-alarm with
   exact dimensions from UsageMetric, support case for denied requests).

**End-to-end scenario:** see
[`skills/service-quotas-usage-auditor/examples/end-to-end.md`](skills/service-quotas-usage-auditor/examples/end-to-end.md)
for an EC2 On-Demand vCPU walkthrough (85% utilization with denied +
pending increase requests) covering first-fail-wins ordering, the
PENDING-vs-applied distinction, Spot-instance redistribution, and
per-region quota independence.

---

### bedrock-guardrail-coverage-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-bedrock-guardrail-coverage`

**What it does:** Audits Amazon Bedrock Guardrails configurations and model
coverage across five dimensions — guardrail existence and status (DRAFT =
zero enforcement, the #1 false sense of security), model/resource coverage
(guardrails are per-request via `guardrailIdentifier`, not per-model — an
application omitting the ID bypasses every filter), content filter strength
(all four core categories: HATE/INSULT/SEXUAL/VIOLENCE, with
outputStrength being the generative-AI-critical axis), contextual grounding
threshold (0.0 = silently disabled — functionally identical to no grounding),
and configuration gaps (empty blocked messaging, DRAFT version in production,
missing PII policy, missing word filters).

**When to invoke (trigger phrases):**

- "audit this Bedrock guardrail"
- "are my Bedrock models protected"
- "check guardrail coverage"
- "content filter too weak"
- "grounding threshold too low"
- "is this guardrail in DRAFT"
- "which models have guardrails"
- "Bedrock agent unguarded"
- "knowledge base guardrail missing"
- "LLM safety audit"

**Example prompt:**

```
You: "This guardrail has HIGH on all filters but 3 of 5 agents don't
     reference it. Is this production-ready?"
```

**Expected behavior:**

1. Classifies the guardrail status (READY passes Step 1; DRAFT →
   NO_GUARDRAIL — zero enforcement).
2. Evaluates model/resource coverage — any resource omitting
   `guardrailIdentifier` is INCOMPLETE_COVERAGE (unguarded despite the
   guardrail existing).
3. Checks all four content categories for `outputStrength: NONE` →
   WEAK_FILTER (output path unprotected).
4. Validates grounding threshold — below 0.2 is WEAK_FILTER (effectively
   disabled despite being configured).
5. Aggregates by precedence: NO_GUARDRAIL > INCOMPLETE_COVERAGE >
   WEAK_FILTER > CONFIG_GAP > OK.
6. Emits VERDICT + RISK + REASON + FINDINGS + REMEDIATION with specific
   CLI per finding (update-agent, update-guardrail,
   create-guardrail-version).

**End-to-end scenario:** see
[`skills/bedrock-guardrail-coverage-auditor/examples/end-to-end.md`](skills/bedrock-guardrail-coverage-auditor/examples/end-to-end.md)
for a multi-finding audit walkthrough (strong guardrail but 3 of 5 resources
unguarded) covering the per-request guardrail model, the outputStrength
asymmetry concept, coverage-percentage reporting, and the
coverage-remediation workflow.

---

### resiliencehub-app-assessment-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-resiliencehub-app-assessment`

**What it does:** Audits AWS Resilience Hub application assessments across
seven dimensions — assessment status (Failed/Pending/InProgress = no data =
CONFIG_GAP, not zero compliance), assessment staleness (>90 days =
STALE_ASSESSMENT, invalidating all downstream compliance data), app-version
drift (assessment references an older appVersion than current), resiliency
policy binding and tier-to-RTO/RPO calibration (MissionCritical with 24h
RTO = miscalibrated), per-tier RTO/RPO compliance (MissionCritical/Critical
NonCompliant = HIGH_RISK; score <50 = systemic HIGH_RISK), aggregate
compliance score (<80 = LOW_COMPLIANCE), and recommendation coverage
(unimplemented Alarm = CONFIG_GAP; unimplemented SDD/Test = informational).
The verdict precedence is STALE_ASSESSMENT > HIGH_RISK > LOW_COMPLIANCE >
CONFIG_GAP > OK, because staleness invalidates every downstream signal and
a MissionCritical-tier breach is qualitatively worse than the same breach
on a Standard-tier component.

**When to invoke (trigger phrases):**

- "audit this resilience hub assessment"
- "is my app assessment stale"
- "check RTO RPO compliance"
- "resiliency policy coverage"
- "assessment freshness check"
- "app version drift resilience hub"
- "compliance score too low"
- "MissionCritical tier non compliant"
- "resilience hub recommendations"
- "resiliency policy not attached"
- "failed assessment no data"
- "resiliency posture check"

**Inputs:** A Resilience Hub app-assessment snapshot — assessment status,
endTime, appVersion, complianceScore, compliance map (per-component tier +
complianceStatus), resiliency policy (tiers with RTO/RPO), and
recommendation inventory (Alarm/SDD/Test counts + implemented counts). For
live-account audits: an app-ARN — the skill emits the AWS CLI commands to
retrieve the full configuration.

**Outputs:** One VERDICT block per app with enumerated FINDINGS (citing the
step and rule) and CLI remediation per finding. The worst finding
determines the verdict; additive findings (version drift, alarm gaps,
policy issues) are retained for context even when a higher-precedence
verdict applies.

**Key expert knowledge deltas (D1):**

1. `list-app-assessments` returns oldest-first by default —
   `--reverse-order --max-results 1` is mandatory to get the latest.
2. A Failed assessment has NO compliance data — classifying it as score 0
   is a false positive (should be CONFIG_GAP, not HIGH_RISK).
3. `PolicyCompliant` proves alignment with the policy, NOT actual resilience
   — a miscalibrated policy (MissionCritical with 7-day RTO) produces a
   perfect score on a broken yardstick.
4. appVersion drift is silent — the assessment shows Success but covers a
   stale published version.
5. Unimplemented Alarm recommendations are operational gaps (detection
   blind spots); unimplemented SDD/Test recommendations are improvement
   opportunities — only the former is verdict-impacting.

**End-to-end scenario:** see
[`skills/resiliencehub-app-assessment-auditor/examples/end-to-end.md`](skills/resiliencehub-app-assessment-auditor/examples/end-to-end.md)
for a multi-finding audit walkthrough (stale assessment with good score,
appVersion drift, and pending alarm recommendations) covering the
staleness-first precedence, version-drift detection, and the
re-assessment remediation workflow.

---

### emr-cluster-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-emr-cluster` — or route via `/aws:pipeline`.

**What it does:** Audits AWS EMR clusters for security configuration across
three encryption layers (S3 at-rest SSE-KMS/CSE-KMS, local-disk at-rest LUKS
via KMS, in-transit TLS), IAM roles (service role, EC2 instance profile,
AutoScaling role), Kerberos authentication, block public access, debug logging,
and instance-group posture. Emits a deterministic verdict
(NO_ENCRYPTION | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK) per cluster with
enumerated findings and specific remediation.

**When to invoke (trigger phrases):**

- "audit this EMR cluster"
- "is my EMR cluster encrypted"
- "check EMR security configuration"
- "EMR IAM role too permissive"
- "EMR in-transit encryption"
- "EMR local disk encryption"
- "Kerberos EMR"
- "block public access EMR"
- "harden EMR cluster"
- reviewing an EMR cluster before production deployment

**Example prompt:**

```
You: "This EMR cluster has SSE-KMS and local-disk encryption but no
     in-transit encryption. The EC2 role has s3:* on *. Audit it before
     production."
```

**Expected behavior:**

1. Applies the ordered classification (encryption gate -> IAM roles ->
   config completeness -> aggregation).
2. Emits VERDICT: NO_ENCRYPTION (Step 1b — InTransit absent). Even though
   the EC2 role is also over-permissive, NO_ENCRYPTION takes precedence.
3. Lists the over-permissive role as an additional finding that would
   produce OVERPERMISSIVE_ROLE if encryption were fixed.
4. Provides remediation: create a new SecurityConfiguration with all three
   layers, scope the EC2 role to specific bucket ARNs, terminate and
   recreate the cluster.

**End-to-end scenario:** see
[`skills/emr-cluster-auditor/examples/end-to-end.md`](skills/emr-cluster-auditor/examples/end-to-end.md)
for a production Spark pipeline walkthrough (full encryption but
over-permissive EC2 instance profile) covering the SecurityConfiguration-as-
separate-API concept, the data-processing-identity insight, and the
credential-refresh-delay remediation caveat.

---

### redshift-cluster-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-redshift-cluster` — or route via `/aws:pipeline`.

**What it does:** Audits Amazon Redshift provisioned clusters for security
posture and configuration gaps across six ordered dimensions — public
accessibility (`PubliclyAccessible: true` is a direct internet endpoint on
TCP 5439/5440), encryption-at-rest (immutable per cluster — the only
remediation is a new-cluster + UNLOAD/COPY migration, not a CLI toggle),
`require_ssl` parameter-group enforcement (the default PG is read-only and
the engine default is `false`), S3 audit logging (CloudTrail covers only
control-plane events, not SQL queries — `enable-logging` is required for
data-plane forensics), automated-snapshot retention (0 disables PITR and
expires existing snapshots within hours), enhanced VPC routing (when off,
COPY/UNLOAD bypasses VPC SGs/NACLs/endpoints), and SG ingress on the
cluster port. Emits a deterministic categorical verdict
(PUBLIC | NO_ENCRYPTION | NO_SSL | NO_AUDIT_LOG | CONFIG_GAP | OK) per
cluster with enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this Redshift cluster"
- "is my Redshift cluster public"
- "is encryption enabled on Redshift"
- "is require_ssl on"
- "is Redshift audit logging configured"
- "are automated snapshots enabled"
- "enhanced VPC routing Redshift"
- "Redshift security group audit"
- "harden this data warehouse"
- "data warehouse compliance audit"
- reviewing a Redshift cluster before production deployment or a
  compliance review

**Example prompt:**

```
You: "This Redshift cluster has PubliclyAccessible true, Encrypted false,
     default.redshift-1.0 parameter group with require_ssl engine-default
     false, LoggingEnabled false, EnhancedVPCRouting false, and the SG
     has 0.0.0.0/0 on TCP 5439. PCI review next week — what's the verdict
     and remediation?"
```

**Expected behavior:**

1. Applies the ordered classification in priority order
   (PUBLIC > NO_ENCRYPTION > NO_SSL > NO_AUDIT_LOG > CONFIG_GAP > OK).
2. Emits VERDICT: PUBLIC (Step 1 — internet-exposed data warehouse).
3. Lists every other dimension failure (NO_ENCRYPTION, NO_SSL,
   NO_AUDIT_LOG, CONFIG_GAP sub-findings) in the FINDINGS list, even
   though PUBLIC is the verdict.
4. Provides specific remediation that reflects Redshift-specific
   behaviours: encryption requires a new-cluster + UNLOAD/COPY migration
   (not a toggle); require_ssl needs a custom PG because the default PG
   is read-only; enable-logging is the API for S3 audit export (distinct
   from the enable_user_activity_logging parameter); EnhancedVPCRouting
   requires a reboot and an S3 Gateway VPC endpoint to function.

**End-to-end scenario:** see
[`skills/redshift-cluster-auditor/examples/end-to-end.md`](skills/redshift-cluster-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (public + Elastic IP + unencrypted +
default-PG no-SSL + no-audit-log + no-EVR + open SG) covering verdict
aggregation, the encryption-is-immutable migration workflow, the
CloudTrail-doesn't-cover-SQL insight, and the default-PG-read-only
remediation ordering.


### opensearch-domain-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-opensearch-domain`

**What it does:** Audits Amazon OpenSearch Service (provisioned, not Serverless)
domains for encryption-at-rest (KMS — customer-managed CMK vs AWS-managed
`aws/es`), node-to-node encryption, fine-grained access control (FGAC /
Advanced Security), public access via resource-policy `Principal: "*"` with
`es:ESHttp*` data-plane grants, dedicated master node type and count
(`t2/t3.small.search` is below AWS recommendation; single master = no HA
quorum), and slow-log publishing to CloudWatch Logs (SEARCH_SLOW_LOGS /
INDEX_SLOW_LOGS). Emits a deterministic verdict
(NO_ENCRYPTION | PUBLIC_ACCESS | NO_FGAC | CONFIG_GAP | OK) per domain with
enumerated findings and specific CLI remediation.

**When to invoke (trigger phrases):**

- "audit this OpenSearch domain"
- "is my OpenSearch domain public"
- "check OpenSearch encryption at rest"
- "OpenSearch node-to-node encryption off"
- "OpenSearch FGAC disabled"
- "is Advanced Security enabled"
- "OpenSearch Principal star"
- "es:ESHttp* public access"
- "dedicated master node too small"
- "t3.small.search dedicated master"
- "OpenSearch slow logs not published"
- "harden OpenSearch domain"
- reviewing an OpenSearch domain before production deployment or compliance audit

**Example prompt:**

```
You: "This internet-facing OpenSearch domain grants es:ESHttp* to
     Principal '*' with no condition. FGAC is off. What's the verdict
     and remediation before we onboard payments traffic?"
```

**Expected behavior:**

1. Applies the ordered classification (encryption → public access → FGAC →
   config gaps → OK).
2. Emits VERDICT: PUBLIC_ACCESS (Step 2a — Principal "*" + es:ESHttp* with
   no STRONG condition is the data-plane blast-radius multiplier).
3. Enumerates NO_FGAC and any CONFIG_GAP findings as additional line items.
4. Provides ordered CLI remediation: remove the wildcard principal, audit
   CloudTrail for `es:ESHttp*` events (assume breach), enable FGAC, plan a
   CMK migration for the AWS-managed key.

**Key distinctions the skill makes:**

- Encryption-at-rest and node-to-node encryption are **immutable** post-
  creation — domain recreation is the only remediation, never a config flip.
- `aws:SourceIp` is NOT a STRONG condition for an OpenSearch public domain
  (bypassable by VPN/NAT). Only `aws:SourceArn` / `aws:SourceAccount` are
  STRONG.
- A VPC-backed domain is never classified PUBLIC_ACCESS regardless of
  access policy — the VPC is the network boundary; FGAC downgrades to
  CONFIG_GAP on VPC domains.
- AWS-managed `aws/es` KMS key is a CONFIG_GAP finding (encrypted but
  operationally opaque — no audit trail, no rotation control, no customer
  key policy), not OK.

**End-to-end scenario:** see
[`skills/opensearch-domain-auditor/examples/end-to-end.md`](skills/opensearch-domain-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (public wildcard + FGAC off + AWS-managed
key) covering worst-finding aggregation, the immutability reasoning for
encryption layers, and the assume-breach remediation workflow.

---

### firehose-delivery-stream-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-firehose-delivery-stream`

**What it does:** Audits Amazon Kinesis Data Firehose delivery streams
for encryption-at-rest gaps (explicit `NoEncryption` opt-out, absent
`EncryptionConfiguration` relying on the S3 bucket default, or valid
SSE-KMS CMK), `BufferingHints` quota violations (`SizeInMBs` 1-128,
`IntervalInSeconds` 60-900), Lambda transformation resilience
(processor buffer parameters, `S3BackupMode: Disabled` silent-corruption
vector), CloudWatch error-logging silence (`LoggingConfig.Enabled: false`
while processing is enabled), source-backup absence under dynamic
partitioning (silent data-loss on JQ extraction failure), and
dynamic-partitioning structural integrity (`MetadataExtraction` wiring,
`ExtendedS3DestinationConfiguration` requirement, `RetryDuration: 0`
immediate-fail trap). Emits a deterministic first-fail-wins verdict
(NO_ENCRYPTION | CONFIG_GAP | OK) per delivery stream with enumerated
findings and CLI remediation.

**When to invoke (trigger phrases):**

- "audit this Firehose delivery stream"
- "is my Firehose stream encrypted"
- "check Firehose Lambda transformation"
- "is dynamic partitioning configured correctly"
- "Firehose source backup missing"
- "CloudWatch error logging disabled Firehose"
- "BufferingHints out of range"
- "firehose data loss vector"
- "firehose NoEncryption destination"
- "firehose silent failure"
- reviewing a delivery stream before production deployment
- validating SSE-KMS CMK coverage on S3 destinations

**Example prompt:**

```
You: "This ExtendedS3 delivery stream has NoEncryption set explicitly,
     DP enabled with RetryDuration 0, and LoggingConfig disabled.
     Audit the data-loss surface."
```

**Expected behavior:**

1. Evaluates encryption first (Step 1) — explicit `NoEncryption: {}`
   fires **NO_ENCRYPTION** and short-circuits all other dimensions.
2. If encryption passes (CMK set), evaluates `BufferingHints` range
   (Step 2) — out-of-range values fire **CONFIG_GAP**.
3. If Lambda processing is enabled, evaluates processor buffer
   parameters and `S3BackupMode` (Step 3) — missing/invalid params or
   `Disabled` mode fires **CONFIG_GAP**.
4. If any processing is enabled, evaluates `LoggingConfig` (Step 4) —
   `Enabled: false` or absent fires **CONFIG_GAP** (silent failure).
5. If dynamic partitioning is enabled, evaluates source backup,
   `RetryDuration`, `MetadataExtraction` wiring, and ExtendedS3
   requirement (Step 5) — any failure fires **CONFIG_GAP**.
6. Aggregates first-fail-wins: NO_ENCRYPTION strictly dominates
   CONFIG_GAP; for CONFIG_GAP, lists all fired findings (multiple gaps
   compound).
7. Emits VERDICT + REASON + FINDINGS + REMEDIATION with specific CLI
   per finding (`update-destination` snippets, CMK policy grants,
   S3BackupConfiguration templates).

**Key expert knowledge deltas (D1):**

1. `NoEncryption: {}` is an explicit, deliberate opt-out — there is no
   "explicit SSE-S3" literal in the API; absence of the block means
   the stream inherits the bucket default (still encrypted in the
   common case).
2. `LoggingConfig` is the in-process error log, NOT delivery metrics —
   `AWS/Firehose` CloudWatch metrics show `DeliveryToS3.Success` as
   green even when records are silently dropped by Lambda.
3. `S3BackupMode: FailedDataOnly` (default) captures only Firehose-
   detected failures; Lambda functions returning 200 with malformed
   output are treated as success and corrupted output is delivered
   without backup.
4. Dynamic partitioning with no `S3BackupConfiguration` is a silent
   data-loss vector — JQ extraction failures on retry exhaustion are
   discarded with no recovery path.
5. `RetryDuration: 0` disables retry entirely; a single extraction
   failure is immediately fatal.
6. `list-delivery-streams` paginates at 10 per page (`--limit` max 10,
   NOT the AWS-typical 50 or 100) — silently truncating the list is
   the most common missed-stream bug.
7. `AWSKMSKeyArn` requires a fully-qualified ARN; aliases are silently
   accepted at creation and fail at first delivery.
8. `update-destination` is not reversible — always capture
   `describe-delivery-stream` output before any update for forensic
   reconstruction.
9. `S3DestinationConfiguration` (legacy) is frozen — no dynamic
   partitioning, no Lambda-aware backup, no `ErrorOutputPrefix`; DP
   enabled on legacy is structurally impossible (API rejects it).
10. Non-S3 destinations (Redshift, Splunk, OpenSearch) stage data in
    S3 first — evaluate the staging `S3BackupConfiguration` for
    encryption and backup even though the user-facing destination is
    the index.

**End-to-end scenario:** see
[`skills/firehose-delivery-stream-auditor/examples/end-to-end.md`](skills/firehose-delivery-stream-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (NO_ENCRYPTION short-circuit +
DP-without-source-backup + LoggingConfig-disabled + RetryDuration=0)
covering first-fail-wins ordering, the NO_ENCRYPTION dominance rule,
the silent data-loss reasoning, and the `update-destination`
remediation workflow.

---

### msk-cluster-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-msk-cluster` — or route via `/aws:pipeline`.

**What it does:** Audits Amazon MSK (Managed Streaming for Kafka) clusters
for encryption in-transit (ClientBroker PLAINTEXT/TLS/TLS_PLAINTEXT +
InClusterEncryption), client authentication (TLS/mTLS via ACM PCA,
SASL/IAM, SASL/SCRAM, unauthenticated), public access
(SERVICE_PROVIDED_EIPS Elastic IPs), broker logging (CloudWatch/S3/
Firehose), and encryption at-rest KMS key governance (customer-managed
CMK vs AWS-managed). Emits a deterministic first-match-wins verdict
(NO_ENCRYPTION | UNAUTHENTICATED | PUBLIC_ACCESS | CONFIG_GAP | OK) per
cluster with enumerated findings and immutability-aware remediation.

**When to invoke (trigger phrases):**

- "audit this MSK cluster"
- "is my Kafka cluster encrypted"
- "check MSK authentication"
- "MSK unauthenticated access"
- "is my MSK cluster public"
- "check MSK broker logging"
- "Kafka plaintext broker"
- "TLS_PLAINTEXT Kafka"
- "harden MSK cluster"
- reviewing an MSK cluster before production deployment
- validating Kafka encryption and authentication posture

**Key expert knowledge deltas (D1):**

1. `TLS_PLAINTEXT` is a dual-mode listener publishing both TLS and
   plaintext ports — clients can bypass TLS entirely. Classified as
   NO_ENCRYPTION, not CONFIG_GAP.
2. MSK encryption settings (ClientBroker, InClusterEncryption,
   authentication modes) are immutable post-creation — remediation
   requires cluster recreation + topic migration, not an in-place CLI fix.
3. MSK always encrypts data volumes at rest — the audit question is key
   governance (customer-managed CMK vs AWS-managed), not encryption
   presence. Missing CMK is CONFIG_GAP, not NO_ENCRYPTION.
4. MSK Serverless enforces TLS + IAM auth and cannot be public —
   applying Provisioned audit logic produces false positives.
5. `InClusterEncryption` is independent from `ClientBroker` — a cluster
   with client TLS but inter-broker plaintext is CONFIG_GAP, not
   NO_ENCRYPTION.
6. SASL/SCRAM secrets must be tagged `AmazonMSK_20181101` in Secrets
   Manager — an untagged secret is invisible to MSK.
7. mTLS requires an ACM Private Certificate Authority (PCA), not a
   self-managed CA upload.
8. Broker logging destinations (CloudWatch, S3, Firehose) are
   independently toggleable — at least ONE must be enabled; Enhanced
   Monitoring and Open Monitoring (Prometheus) are NOT log delivery.

**End-to-end scenario:** see
[`skills/msk-cluster-auditor/examples/end-to-end.md`](skills/msk-cluster-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (TLS_PLAINTEXT NO_ENCRYPTION short-circuit
+ all broker logging disabled) covering first-match-wins priority, the
TLS_PLAINTEXT-vs-TLS distinction, and the immutability-aware migration
remediation workflow.

---

### cleanrooms-collaboration-auditor

**Pipeline phase:** Phase 2 — Audit.

**Slash command:** `/aws:audit-cleanrooms-collaboration` — or route via
`/aws:pipeline`.

**What it does:** Audits AWS Clean Rooms collaborations across four
orthogonal dimensions — membership activation (INVITED/REMOVED/LEFT
members, solo collaborations, no CAN_QUERY member), privacy-budget
posture (differential privacy disabled, per-member epsilon near-
exhaustion >=80% of cap, aggregate constraints absent), analysis-
template SQL validity (dangling configured-table aliases, unresolved
`${param}` tokens, columns outside allowedColumns), and configured-
audience readiness (cleanroomsml model not READY, stale training data,
missing destinationConfig). Emits a deterministic verdict
(MEMBERSHIP_GAP | PRIVACY_RISK | CONFIG_GAP | OK) per collaboration
with enumerated findings and per-rule CLI remediation.

**When to invoke (trigger phrases):**

- "audit this Clean Rooms collaboration"
- "check Clean Rooms member status"
- "is differential privacy enabled"
- "epsilon budget exhausted"
- "validate analysis template SQL"
- "is my audience model trained"
- "Clean Rooms membership gap"
- "configured audience ready"
- "privacy budget audit"
- "protected query failed"
- "Clean Rooms collaboration posture"
- reviewing a collaboration before opening production query traffic
- validating membership activation across multi-party collaborators

**Inputs:** A Clean Rooms collaboration snapshot — collaboration
metadata (status, creatorDisplayName, queryLogStatus, analyticsEngine,
configuredAudienceModelArn), member list with status and abilities,
differential privacy config (enabled, epsilonBudgetPerMember),
per-member epsilon spend (summed from ListProtectedQueries), configured
tables with allowedColumns and aggregateConstraints, analysis-template
bodies with parameters, and configured-audience-model state from
`cleanroomsml get-configured-audience-model`. For live-account audits:
a collaboration ARN or ID — the skill emits the AWS CLI commands to
retrieve the full configuration.

**Outputs:** One VERDICT block per collaboration with enumerated
FINDINGS citing rule numbers (M1-M4, P1-P4, A1-A4, Q1-Q2, C1-C3) and
CLI remediation per finding. The worst finding determines the verdict
by precedence (MEMBERSHIP_GAP > PRIVACY_RISK > CONFIG_GAP > OK);
additive findings (privacy gaps, template defects, audience gaps) are
retained for parallel remediation even when a higher-precedence
verdict applies.

**Key expert knowledge deltas (D1):**

1. Membership status is perspective-relative — `ListMembers` returns
   the collaboration's view; `GetMembership` returns the caller's own
   view. A member can be ACTIVE from the creator's perspective but
   LEFT from their own — a silent MEMBERSHIP_GAP that surfaces only
   when queries fail with AccessDeniedException.
2. Epsilon is per-member, not per-collaboration — each member has
   their OWN budget. One member at 95% spend and another at 5% is not
   uniformly healthy; the high-spend member is the bottleneck. Report
   per-member, not aggregate.
3. `differentialPrivacyConfig.enabled: true` is the capability gate,
   not enforcement. The per-query `additionalAnalyses` epsilon is the
   enforcement — a query with `additionalAnalyses: 0` runs without DP
   noise even on a DP-enabled collaboration.
4. Aggregate constraints (MIN/MAX) are the structural privacy floor;
   DP is the noise layer on top. A collaboration with DP enabled but
   no aggregate constraints can still return singleton rows when noise
   rounds a 1-row group up to threshold. Both layers must be present.
5. Analysis templates are immutable per-creation, but the configured
   tables they reference ARE mutable — a member removing their table
   after the template was created produces a runtime-only failure
   (ResourceNotFoundException) with no live validator.
6. Configured audiences live in `cleanroomsml`, not `cleanrooms` — the
   collaboration references the ARN; the state lives in a separate
   service. A collaboration can show a valid ARN while the model is in
   CREATE_FAILED. Always fetch the model state separately.
7. Epsilon budget does NOT reset at any calendar boundary — it is
   monotonic per member per collaboration. Increasing it requires
   recreating the collaboration.
8. Protected queries return S3 Parquet prefixes, not rows — a
   `SUCCEEDED` query plus a bucket policy that blocks member reads
   produces a silent empty result. Cross-reference the S3 destination.
9. `queryLogStatus` is a one-way, set-at-creation flag — enabling it
   post-hoc requires deleting and recreating the collaboration. Treat
   DISABLED as a CONFIG_GAP note, not a privacy verdict driver.

**End-to-end scenario:** see
[`skills/cleanrooms-collaboration-auditor/examples/end-to-end.md`](skills/cleanrooms-collaboration-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (INVITED member MEMBERSHIP_GAP + DP
disabled PRIVACY_RISK + missing aggregate constraints) covering
precedence aggregation, the per-member epsilon reasoning, the
"enabled ≠ enforced" DP distinction, and the privacy-controls-before-
activation remediation ordering.

---

## /aws:audit-lakeformation-data-lake

**Slash command:** `/aws:audit-lakeformation-data-lake`
**Skill:** `lakeformation-data-lake-auditor` (family: Analytics, phase: 2 Audit)
**Verdict shape:** `OVERPERMISSIVE_GRANT | EXTERNAL_ACCOUNT | CONFIG_GAP | OK`

Audit a Lake Formation data lake for grant-level exposure and configuration
gaps. Reads `list-permissions` output paired with `get-data-lake-settings`,
`list-resources`, and `list-data-cells-filter` metadata, and applies ordered
classification logic across 10 steps to emit a deterministic verdict per data
lake.

**Inputs:** `list-permissions` (grants), `get-data-lake-settings`
(`DataLakeAdmins`, `CreateDatabaseDefaultPermissions`,
`CreateTableDefaultPermissions`), `list-resources` (registered S3 locations
and their `RoleArn`), `list-data-cells-filter` (existing row-level filters),
optionally `get-resource-lf-tags` and `describe-organization`.

**Outputs:** One VERDICT block per data lake with enumerated FINDINGS (citing
the step and rule) and CLI remediation per finding. The worst finding
determines the verdict; additive findings (cell-filter gap, empty admins) are
retained even when a higher-precedence verdict applies.

**Key expert knowledge deltas (D1):**

1. Lake Formation has NO Deny — permissions are purely additive. The only
   way to block access is to refrain from granting or call
   `RevokePermissions`. You cannot layer a Deny on an over-broad Allow.
2. `IAMAllowedPrincipals` is a SPECIAL PRINCIPAL that opts the resource OUT
   of LF enforcement (IAM policy becomes the sole authority) — it does NOT
   mean "all IAM principals". A database with `IAMAllowedPrincipals` AND
   explicit LF grants on its tables is in mixed mode (both layers evaluate;
   EITHER allowing grants access).
3. `WithGrantablePermissions` chains UNBOUNDED — unlike KMS grants (capped
   at 2 levels), an LF grantee can re-delegate indefinitely.
4. `ColumnWildcard: {}` is the real column wildcard; `ColumnNames: ["*"]`
   is a literal column named `*` (silently empty — broken automation).
5. `Table` and `TableWithColumns` are SEPARATE resource types — SELECT on
   `Table` is implicit all-columns-all-rows; only `TableWithColumns`
   supports column scoping.
6. `DataCellsFilter` must be CREATED and WIRED via grant — a filter that
   exists but is not referenced by any SELECT grant is a silent gap.
7. Cross-account sharing uses RAM; the recipient sees nothing until an admin
   creates a Resource Link AND grants on it. Source revoke does NOT delete
   recipient resource links.
8. `Permission: ALL` on `Catalog` is functionally data-lake administrator
   (the grantee can grant anything to anyone, including themselves).
9. Quota: 50,000 LF grants per account (soft cap) — remediations that ADD
   grants can hit the cap and fail silently.
10. Registered-location `RoleArn` is the service role LF uses to read S3;
    if the role is deleted, every grant on tables under that location is
    dead (queries fail with S3 `AccessDenied`, not LF).

**End-to-end scenario:** see
[`skills/lakeformation-data-lake-auditor/examples/end-to-end.md`](skills/lakeformation-data-lake-auditor/examples/end-to-end.md)
for a multi-finding walkthrough (ColumnWildcard SELECT on a PII table +
WithGrantablePermissions delegation + empty DataLakeAdmins) covering
OVERPERMISSIVE_GRANT aggregation, the no-Deny / revoke-after-replace
remediation ordering, the unbounded-delegation forensics extension, and the
DataCellsFilter wiring gap.

---

## Eval Status

Each skill carries a co-located eval specification (`eval/test-cases.yaml`)
and a committed LLM-judge scorecard (`eval/scorecards/<skill>.json`). Run the
assertion layer:

```bash
python3 eval/run_eval.py --assertion-only
```

Run the full LLM-judge eval locally (requires AWS SSO):

```bash
python3 eval/run_eval.py --profile default
```

See [docs/skill-judge-dashboard.md](docs/skill-judge-dashboard.md) for the
per-skill scorecard dashboard.
