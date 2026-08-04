# AWS CloudOps Service Taxonomy — Shared Reference

**Why this file exists:** Cross-cutting reference loaded by any skill that
needs to understand the full AWS service landscape, which family a service
belongs to, and whether a dedicated auditor skill exists. This is the lean
inventory; each specialist skill owns its own service-specific depth.

Grounded in the botocore service enumeration: 421 total services, 287
CloudOps-relevant, organized into 12 families.

---

## The 12 CloudOps families

| Family | Services | High-feas | This family audits |
|---|---|---|---|
| Security & Identity | 40 | 19 | IAM, KMS, GuardDuty, Security Hub, WAF, Secrets Manager, ACM, Cognito, STS, Shield, Macie, Inspector, Firewall Manager, Access Analyzer, Network Firewall, Detective, Security Lake, Identity Center, Verified Permissions, Signer, RAM, Roles Anywhere, CloudHSM, Directory Service, AppFabric, Sign-in, Payment Cryptography, Security IR, Security Agent |
| Management & Monitoring | 42 | 7 | CloudFormation, CloudWatch, CloudWatch Logs, Systems Manager, Health, Service Quotas, Resilience Hub, AppConfig, DevOps Guru, X-Ray, Synthetics, AMP, Grafana, Observability Admin, OAM, CloudControl, Application Signals, Application Insights, Performance Insights, Support, Sustainability, Account, Chatbot, Notifications, Resource Explorer, Resource Groups, RUM, FIS, SSM Contacts, SSM Incidents, SSM Quick Setup, SSM SAP, Launch Wizard, Service Catalog, AppRegistry, AIOps, ARC, Cloud Directory, Notifications Contacts, SSM GUI Connect, AppConfig Data |
| Compute & Containers | 24 | 7 | EC2, Lambda, ECS, EKS, ECR, Auto Scaling, Compute Optimizer, App Runner, Batch, Elastic Beanstalk, Image Builder, MWAA, Outposts, EKS Auth, ECR Public, EC2 Instance Connect, Lightsail, Proton, EVS, PCS, Autoscaling Plans, Compute Optimizer Automation, MWAA Serverless |
| Databases | 24 | 2 | RDS, DynamoDB, ElastiCache, DocumentDB, Redshift, OpenSearch, Neptune, MemoryDB, Keyspaces, Aurora DSQL, DynamoDB Streams, Timestream, DAX, DocDB Elastic, Neptune Graph, Redshift Serverless, OpenSearch Serverless, RDS Data, Redshift Data, Neptune Data, ODB, Keyspaces Streams, Timestream InfluxDB, Timestream Query, Timestream Write |
| Networking & CDN | 22 | 6 | CloudFront, Route 53, ELBv2, Direct Connect, Global Accelerator, Network Manager, App Mesh, ELB, VPC Lattice, Internet Monitor, Network Flow Monitor, Service Discovery, Route 53 Resolver, Route 53 Domains, Network Firewall, TNB, CloudFront KVS, Network Monitor, Route 53 ARC, Route 53 Global Resolver, Route 53 Profiles |
| Analytics | 22 | 1 | Kinesis, Athena, Glue, MSK (Kafka), OpenSearch, Redshift, Firehose, Lake Formation, EMR, Clean Rooms, DataSync, DataZone, DataBrew, DataExchange, Entity Resolution, Elasticsearch, Kafka Connect, EMR on EKS, EMR Serverless, Kinesis Analytics, Kinesis Analytics v2, OSIS |
| Application Integration | 18 | 6 | SQS, SNS, EventBridge, Step Functions, API Gateway, API Gateway v2, AppSync, EventBridge Pipes, EventBridge Scheduler, EventBridge Schemas, SES, SES v2, Amazon MQ, AppFlow, AppIntegrations, B2Bi, Serverless Application Repo, API Gateway Management |
| Developer Tools | 18 | 5 | CodeBuild, CodeCommit, CodeDeploy, CodePipeline, CodeGuru Security, CodeArtifact, CodeGuru Reviewer, CodeConnections, CodeStar Connections, Cloud9, Amplify, Amplify Backend, Amplify UI Builder, CodeCatalyst, CodeStar Notifications, Device Farm, CodeGuru Profiler, DevOps Agent |
| Storage | 18 | 6 | S3, S3 Control, EBS, EFS, Backup, DLM, FSx, Glacier, Storage Gateway, Transfer Family, Snowball, Snow Device Management, Recycle Bin, Backup Gateway, Backup Search, S3 Outposts, S3 Tables, S3 Vectors |
| AI/ML | 17 | 2 | Bedrock, SageMaker, Bedrock Agents, Bedrock Runtime, Bedrock AgentCore, Nova Act, Bedrock Data Automation, Elemental Inference, SageMaker Runtime, SageMaker A2I, SageMaker Edge, SageMaker Feature Store, SageMaker Geospatial, SageMaker Metrics, Bedrock Agent Runtime, Bedrock AgentCore Control, Bedrock Data Automation Runtime |
| FinOps & Billing | 16 | 6 | Billing, Budgets, Cost Explorer, Cost Optimization Hub, CUR, Savings Plans, Billing Conductor, BCM Data Exports, Free Tier, Tax Settings, Application Cost Profiler, BCM Dashboards, BCM Pricing Calculator, BCM Recommended Actions, Invoicing, Pricing |
| Governance & Compliance | 15 | 7 | CloudTrail, Config, Organizations, Control Tower, Well-Architected, Trusted Advisor, Audit Manager, Artifact, Control Catalog, License Manager, Tagging API, RTBFabric, CloudTrail Data, License Manager Linux Subscriptions, License Manager User Subscriptions |
| Migration & Modernization | 11 | 3 | DMS, DRS, MGN, Application Discovery, Migration Hub, Mainframe Modernization, Migration Hub Orchestrator, Migration Hub Strategy, Refactor Spaces, Migration Hub Config, MPA |

## Eval-feasibility definitions

- **High:** deterministic verdict (SAFE/PUBLIC/AMBIGUOUS, PASS/FAIL), single
  `Describe*` API call. 77 services total.
- **Medium:** config-audit applicable, some metric-based assertions. 114 services.
- **Low:** data-plane operations, transient state, or niche API surface. 96 services.

## Current skill coverage

| Family | Skills shipped | Contributor backlog |
|---|---|---|
| Security & Identity | iam-least-privilege-advisor | 39 remaining (KMS, GuardDuty, WAF, Secrets Manager, ACM, etc.) |
| Compute & Containers | ec2-security-group-auditor | 23 remaining (Lambda, ECS, EKS, ECR, etc.) |
| Storage | s3-public-access-auditor | 17 remaining (EBS, EFS, Backup, etc.) |
| All other families | 0 | 208 remaining |

**Total shipped:** 3 seeds + 1 orchestrator = 4. **Planned:** 90 (Phase 3-10).
**Contributor backlog:** 197 services documented with audit descriptions.
