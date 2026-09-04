# Governance skills (29)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `account-factory-deployer` | deploy | Deploys AWS Control Tower Account Factory accounts with production defaults: account creation via Service Catalog product (provision-product), Organiz |
| `auditmanager-assessment-auditor` | audit | Audits AWS Audit Manager assessments for evidence-collection integrity, control compliance rate, delegation wiring, and account-level settings posture |
| `auto-remediation-automator` | automate | Designs and implements automated remediation workflows linking AWS Config rules to SSM Automation runbooks. |
| `cloudtrail-alert-automator` | automate | Designs and deploys CloudTrail alerting automation across an AWS estate. |
| `cloudtrail-cost-optimizer` | optimize | Optimises AWS CloudTrail cost across seven dimensions: trail consolidation (single organization trail replaces N per-region or member-account trails,  |
| `cloudtrail-gap-troubleshooter` | troubleshoot | Diagnoses AWS CloudTrail logging gaps and missing events. |
| `cloudtrail-lake-operator` | operate | Operates AWS CloudTrail Lake end-to-end — Event Data Store (EDS) creation with the full ingestion surface (CloudTrail management events, CloudTrail da |
| `cloudtrail-lake-query-deployer` | deploy | Provisions AWS CloudTrail Lake with production defaults: event data store (EDS) creation, ingestion (management events, data events, Insights), SQL qu |
| `cloudtrail-missing-events-troubleshooter` | troubleshoot | Diagnoses AWS CloudTrail missing-events incidents across eleven failure categories: trail logging inadvertently disabled (stop-logging, IaC that omitt |
| `cloudtrail-org-trail-auditor` | audit | Audits AWS CloudTrail organization trails for full-org coverage, multi-region logging, KMS encryption (SSE-KMS) of log delivery, log-file validation ( |
| `config-aggregator-deployer` | deploy | Provisions AWS Config aggregators with correct production defaults: organization aggregator (AWS Organizations delegated administrator), authorized ac |
| `config-recorder-coverage-auditor` | audit | Audits AWS Config posture across all four coverage layers — configuration recorder (existence, status, resource-type scope), delivery channel (S3 deli |
| `config-rule-compliance-automator` | automate | Designs and deploys AWS Config rule compliance automation across an AWS estate. |
| `config-rule-deployer` | deploy | Provisions AWS Config rules with compliance coverage: managed rules (100+ AWS-managed like s3-bucket-public-read-prohibited, iam-user-no-policies), cu |
| `controltower-control-auditor` | audit | Audits AWS Control Tower landing-zone state, enabled controls (preventive, detective, proactive), guardrail enforcement integrity, and account-factory |
| `drift-detection-automator` | automate | Designs and implements automated CloudFormation drift detection workflows across single-account and multi-account environments. |
| `lakeformation-permissions-deployer` | deploy | Deploys AWS Lake Formation permissions with production-grade config: LF-tag based access control (tag keys and values, tag-based grants on databases,  |
| `license-manager-deployer` | deploy | Provisions AWS License Manager configurations with production defaults: license configurations (license type, count, rules), resource associations (EC |
| `multi-account-governance-automator` | automate | Designs AWS multi-account governance automation spanning Organizations (OU hierarchy, account creation, SCP guardrail/throttle/deny strategies), Contr |
| `organizations-account-deployer` | deploy | Provisions AWS Organizations member accounts with production defaults: account creation (create-account with unique root email, IAM role name), Contro |
| `organizations-policy-deployer` | deploy | Deploys AWS Organizations policy artifacts with production defaults: Service Control Policy (SCP) creation (JSON policy via create-policy), attachment |
| `organizations-scp-auditor` | audit | Audits AWS Organizations Service Control Policies (SCPs) for effective permission boundaries across the OU hierarchy — FullAWSAccess inheritance, deny |
| `ram-resource-share-deployer` | deploy | Provisions AWS RAM (Resource Access Manager) resource shares with correct production defaults: resource type selection (Subnet, Transit Gateway, Licen |
| `service-catalog-portfolio-deployer` | deploy | Provisions AWS Service Catalog portfolios and products with production-safe defaults: portfolio creation (DisplayName, ProviderName, description), pro |
| `tag-compliance-automator` | automate | Automates AWS tag compliance end-to-end: Organizations tag policies with case-sensitive key/value validation and enforced_for scoping, Resource Groups |
| `tag-governance-automator` | automate | Designs and implements AWS tag governance automation across Organizations TagPolicy JSON (allowed_values, case_sensitive, enforced_for cascade), Event |
| `trustedadvisor-check-auditor` | audit | Audits AWS Trusted Advisor check results across cost optimization, performance, security, fault tolerance, and service-limits pillars for actionable f |
| `wellarchitected-review-operator` | operate | Operates AWS Well-Architected Tool reviews end-to-end — creates workloads, runs pillar reviews (operational excellence, security, reliability, perform |
| `wellarchitected-workload-auditor` | audit | Audits AWS Well-Architected Tool workloads for review staleness, per-pillar high-risk issue counts, milestone tracking gaps, and remediation plan comp |
