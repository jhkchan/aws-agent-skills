# Management skills (43)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `appconfig-deployment-operator` | operate | Operates AWS AppConfig deployment lifecycles safely — creates applications, environments, and configuration profiles (freeform and feature-flag); defi |
| `aws-orchestrator` | audit | Start here for any AWS CloudOps audit, security review, compliance check, or infrastructure assessment. |
| `cloudwatch-alarm-auditor` | audit | Audits CloudWatch alarm configurations for blind spots across six dimensions: detection strategy (anomaly detection vs static threshold), action wirin |
| `cloudwatch-alarm-notification-automator` | automate | Designs CloudWatch alarm notification and escalation automation across six surfaces: SNS-to-Lambda forwarders for Slack / Teams / PagerDuty / Opsgenie |
| `cloudwatch-alarm-operator` | operate | Operates CloudWatch alarm lifecycles safely — creates static-threshold, metric-math, anomaly-detection, and composite alarms; tunes threshold / period |
| `cloudwatch-alarm-troubleshooter` | troubleshoot | Diagnoses CloudWatch alarm issues through a nine-category diagnostic tree: alarm stuck in INSUFFICIENT_DATA (missing metric, missing dimension, period |
| `cloudwatch-anomaly-detector-deployer` | deploy | Deploys Amazon CloudWatch Anomaly Detection models on AWS metrics with production defaults: anomaly detector creation (put-metric-anomaly-detector), m |
| `cloudwatch-application-signals-deployer` | deploy | Enables CloudWatch Application Signals on ECS / EKS / EC2 / Lambda with auto-instrumentation (Java, Python), service discovery from CloudMap and Kuber |
| `cloudwatch-application-signals-operator` | operate | Operates AWS CloudWatch Application Signals with production defaults: enablement via OpenTelemetry (OTel) SDK instrumentation or auto-instrumentation, |
| `cloudwatch-cross-account-observability-deployer` | deploy | Provisions CloudWatch cross-account observability via Observability Access Manager (OAM) — creates the monitoring account sink, attaches source accoun |
| `cloudwatch-dashboard-deployer` | deploy | Provisions CloudWatch dashboards with widget layouts, metric selections, and sharing models. |
| `cloudwatch-dashboards-operator` | operate | Operates Amazon CloudWatch dashboards end-to-end — dashboard creation and update via JSON model (PutDashboard/GetDashboard API), custom widgets backed |
| `cloudwatch-logs-cost-optimizer` | optimize | Optimises Amazon CloudWatch Logs cost across six dimensions: log group retention (Never expire is the #1 waste — moving to 30 days typically cuts stor |
| `cloudwatch-logs-insights-troubleshooter` | troubleshoot | Diagnoses CloudWatch Logs Insights problems across six categories: query returns no results (wrong log group, time range outside ingestion, filter cas |
| `cloudwatch-logs-not-ingesting-troubleshooter` | troubleshoot | Diagnoses CloudWatch Logs not-ingesting scenarios through a thirteen-category diagnostic tree: log group vs log stream naming, IAM permissions for Put |
| `cloudwatch-logs-retention-auditor` | audit | Audits CloudWatch Logs log groups for Never-expire retention (silent infinite-cost accumulation), missing SSE-KMS customer-managed-key (CMK) encryptio |
| `cloudwatch-metric-stream-deployer` | deploy | Deploys Amazon CloudWatch Metric Streams with production defaults: stream creation (name, output format), Kinesis Data Firehose ARN configuration, met |
| `cloudwatch-metrics-troubleshooter` | troubleshoot | Diagnoses missing or unexpected AWS CloudWatch metrics. |
| `cloudwatch-rum-deployer` | deploy | Provisions CloudWatch RUM (Real User Monitoring) app monitors with production-grade defaults — domain allow-list, sample rate, cookie domain, telemetr |
| `cloudwatch-synthetics-troubleshooter` | troubleshoot | Diagnoses CloudWatch Synthetics canary failures via a symptom-to-cause decision tree covering all five canary types (GUI Selenium WebDriver, HTTP ping |
| `devops-guru-troubleshooter` | troubleshoot | Diagnoses Amazon DevOps Guru insights across Proactive and Reactive categories. |
| `dr-failover-automator` | automate | Designs AWS disaster recovery failover automation across the four DR strategies (backup & restore, pilot light, warm standby, multi-site active/active |
| `fis-experiment-deployer` | deploy | Provisions AWS Fault Injection Service (FIS) experiment templates with production-safe defaults: action targets (tags, ARNs, filters), fault actions a |
| `fis-template-deployer` | deploy | Provisions AWS Fault Injection Simulator (FIS) experiment templates with production defaults: experiment template creation (JSON), action specificatio |
| `grafana-dashboard-deployer` | deploy | Provisions Amazon Managed Grafana workspaces and dashboards with production defaults: workspace creation (authentication via SSO or IAM Identity Cente |
| `grafana-data-source-deployer` | deploy | Provisions Amazon Managed Grafana workspaces with production defaults: workspace creation, SAML/SSO authentication, data source configuration (CloudWa |
| `greengrass-component-deployer` | deploy | Deploys AWS IoT Greengrass v2 components with production defaults: component recipe YAML (lifecycle hooks: install, startup, shutdown), component vers |
| `health-event-auditor` | audit | Audits AWS Health for active (open) issue events, upcoming scheduled changes, affected-resource entity status, closed-event resolution, Health Dashboa |
| `health-event-automator` | automate | Designs AWS Health event response automation across the three event type categories (issue, accountNotification, scheduledChange), EventBridge rules r |
| `log-retention-automator` | automate | Designs and implements CloudWatch Logs retention automation workflows. |
| `resiliencehub-app-assessment-auditor` | audit | Audits AWS Resilience Hub application assessments for assessment staleness (older than 90 days), resiliency policy binding and tier-to-RTO/RPO calibra |
| `service-quotas-usage-auditor` | audit | Audits AWS Service Quotas — quota utilization per service, approaching limits (>=80%), CloudWatch alarm coverage on AWS/Usage metrics, applied vs defa |
| `sitewise-asset-deployer` | deploy | Deploys AWS IoT SiteWise industrial data infrastructure with production defaults: asset model creation (measurement, metric, transform, attribute prop |
| `ssm-association-operator` | operate | Operates AWS Systems Manager (SSM) State Manager associations with production defaults: association creation (document name, targets, schedule), assoc |
| `ssm-association-troubleshooter` | troubleshoot | Diagnoses AWS Systems Manager (SSM) association failures via a systematic 5-symptom decision tree: association status Failed, TimedOut, instance not a |
| `ssm-automation-deployer` | deploy | Provisions AWS Systems Manager (SSM) Automation documents with production defaults: document type (Automation, Command, Session), schema version, para |
| `ssm-managed-instance-auditor` | audit | Audits AWS Systems Manager (SSM) managed instances across six dimensions — instance coverage (SSM Agent reachable + IAM profile attached), association |
| `ssm-patch-baseline-deployer` | deploy | Provisions SSM Patch Baselines with secure patch-management defaults — baseline creation (OS, product, classification, severity), approval rules (auto |
| `ssm-patch-compliance-automator` | automate | Designs and implements SSM Patch Manager automation workflows for EC2 fleets. |
| `ssm-patch-operator` | operate | Operates SSM Patch Manager workflows safely — patch baseline authoring (AWS-managed and custom), patch group tag targeting, AWS-RunPatchBaseline Scan  |
| `ssm-session-manager-troubleshooter` | troubleshoot | Diagnoses AWS Systems Manager (SSM) Session Manager failures via a systematic 7-symptom decision tree: target instance not reachable (SSM agent not ru |
| `ssm-session-troubleshooter` | troubleshoot | Diagnoses AWS Systems Manager Session Manager failures through a thirteen-category diagnostic tree: managed instance not showing up (SSM Agent not run |
| `xray-tracing-deployer` | deploy | Deploys AWS X-Ray distributed tracing with production-grade configuration: X-Ray daemon deployment (EC2 systemd, ECS sidecar, EKS DaemonSet, Lambda bu |
