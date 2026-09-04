# Analytics skills (41)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `athena-query-failure-troubleshooter` | troubleshoot | Diagnoses Amazon Athena query failures through a thirteen-category diagnostic tree: S3 bucket access denied (Glue Data Catalog vs S3 data bucket permi |
| `athena-query-optimizer` | optimize | Optimizes Amazon Athena query performance and cost via a layered analysis framework covering partitioning (partition projection, dynamic partition pru |
| `athena-workgroup-auditor` | audit | Audits Amazon Athena workgroups for query-result encryption gaps (S3 + KMS), missing data-scan limits (BytesScannedCutoffPerQuery), workgroup enforcem |
| `cleanrooms-collaboration-auditor` | audit | Audits AWS Clean Rooms collaborations for membership-status gaps (INVITED or REMOVED members), privacy-budget risks (differential privacy disabled, ep |
| `dataexchange-dataset-deployer` | deploy | Deploys AWS Data Exchange data sets with production defaults: subscription creation (data product from providers), asset export to S3, revision auto-e |
| `datazone-domain-deployer` | deploy | Provisions Amazon DataZone data domains with production defaults: domain creation (create-datazone-domain), project management, data source connection |
| `emr-cluster-auditor` | audit | Audits AWS EMR clusters for security configuration across three encryption layers (S3 at-rest, local-disk at-rest, in-transit TLS), IAM roles (service |
| `emr-serverless-deployer` | deploy | Deploys Amazon EMR Serverless applications with production-grade configuration: application creation (release label, type: Spark or Hive), capacity co |
| `firehose-delivery-stream-auditor` | audit | Audits Amazon Kinesis Data Firehose (firehose) delivery streams for encryption-at-rest gaps (explicit NoEncryption, missing CMK, or absent EncryptionC |
| `firehose-delivery-stream-deployer` | deploy | Provisions Kinesis Data Firehose delivery streams with production defaults: source selection (Direct PUT, Kinesis Data Stream, Amazon MSK, CloudWatch  |
| `glue-crawler-deployer` | deploy | Provisions AWS Glue Crawlers with production defaults: data source configuration (S3, DynamoDB, JDBC), IAM role with least-privilege permissions, clas |
| `glue-crawler-job-auditor` | audit | Audits AWS Glue crawlers and jobs (plus their data-catalog encryption, JDBC connections, IAM execution roles, security configurations, job bookmarks,  |
| `glue-job-failure-troubleshooter` | troubleshoot | Diagnoses AWS Glue job failures through a fifteen-layer diagnostic tree: ETL script errors (PySpark/Scala exceptions), DPU allocation insufficient (ex |
| `glue-job-troubleshooter` | troubleshoot | Diagnoses AWS Glue ETL job failures through a seven-category diagnostic tree — Python script exceptions (KeyError, AttributeError, import errors), job |
| `kafka-connect-troubleshooter` | troubleshoot | Diagnoses Kafka Connect and Amazon MSK Connect issues through a nine-category diagnostic tree — task FAILED status (task exceptions), worker rebalance |
| `kafka-msk-lag-troubleshooter` | troubleshoot | Diagnoses Amazon MSK consumer lag through a ten-category diagnostic tree: consumer-group lag (RecordsLagMax) vs consumer processing rate, partition sk |
| `kafka-msk-troubleshooter` | troubleshoot | Diagnoses Amazon MSK (Managed Streaming for Apache Kafka) cluster issues via a symptom-to-cause decision tree covering broker failures (describe-clust |
| `kinesis-analytics-deployer` | deploy | Deploys Amazon Kinesis Data Analytics applications (Managed Service for Apache Flink and Studio SQL) with production-grade config: application creatio |
| `kinesis-firehose-troubleshooter` | troubleshoot | Diagnoses Amazon Kinesis Data Firehose delivery stream failures via a systematic 8-symptom decision tree: delivery to S3 fails (bucket deleted, KMS ke |
| `kinesis-stream-auditor` | audit | Audits Amazon Kinesis Data Streams for encryption-at-rest gaps (EncryptionType NONE), extended-retention cost exposure, shard-count quota-exhaustion r |
| `kinesis-stream-deployer` | deploy | Provisions Amazon Kinesis Data Streams with production defaults: stream creation (shard count, stream mode provisioned vs on-demand), enhanced fan-out |
| `lakeformation-data-lake-auditor` | audit | Audits AWS Lake Formation data-lake posture for catalog-level super-grants, cross-account principals, ColumnWildcard SELECT without DataCellsFilter, W |
| `managed-blockchain-deployer` | deploy | Provisions AWS Managed Blockchain with production defaults: Hyperledger Fabric network creation (edition Starter vs Standard, framework version, votin |
| `msk-cluster-auditor` | audit | Audits Amazon MSK (Managed Streaming for Kafka) clusters for encryption in-transit (TLS between clients and brokers, inter-broker), encryption at-rest |
| `msk-cost-optimizer` | optimize | Optimises Amazon MSK cost across seven dimensions — broker type right-sizing (CloudWatch BytesInPerSec, KafkaDataLogsDiskUsed, consumer lag MaxOffsetL |
| `mwaa-environment-deployer` | deploy | Provisions Amazon Managed Workflows for Apache Airflow (MWAA) environments with production defaults: environment creation (create-environment), Airflo |
| `opensearch-alerting-deployer` | deploy | Provisions Amazon OpenSearch Service alerting configurations with production defaults: monitor creation (query monitor vs cluster metrics monitor vs p |
| `opensearch-cluster-troubleshooter` | troubleshoot | Diagnoses Amazon OpenSearch Service cluster incidents across eleven failure categories: ClusterBlockException from disk watermark breach (85% flood-st |
| `opensearch-domain-auditor` | audit | Audits Amazon OpenSearch Service (provisioned, not Serverless) domains for encryption-at-rest (KMS), node-to-node encryption, fine-grained access cont |
| `opensearch-domain-deployer` | deploy | Provisions Amazon OpenSearch Service domains with production defaults: deployment type (managed cluster vs Serverless), instance type (t3.small.search |
| `opensearch-index-deployer` | deploy | Provisions Amazon OpenSearch Service indices with production defaults: index creation with explicit mappings (dynamic vs strict), shard count (primary |
| `opensearch-migration-operator` | operate | Operates Elasticsearch to OpenSearch migration workflows safely — version compatibility assessment (ES 5.x/6.x/7.x to OpenSearch 1.x/2.x), index migra |
| `opensearch-serverless-deployer` | deploy | Provisions Amazon OpenSearch Serverless collections with secure defaults — collection type selection (SEARCH, TIMESERIES, VECTORSEARCH), encryption po |
| `opensearch-snapshot-troubleshooter` | troubleshoot | Diagnoses Amazon OpenSearch Service snapshot failures through a thirteen-category diagnostic tree: S3 repository registration errors (PUT _snapshot),  |
| `quicksight-dashboard-deployer` | deploy | Provisions Amazon QuickSight dashboards with production defaults: account creation (Standard/Enterprise), data source (Athena, RDS, Redshift, S3, Auro |
| `redshift-cluster-auditor` | audit | Audits Amazon Redshift provisioned clusters for security posture and configuration gaps — public accessibility (internet-exposed cluster), KMS encrypt |
| `redshift-cluster-optimizer` | optimize | Optimises Amazon Redshift cluster cost and performance through node-type selection (RA3 managed-storage compute-separated vs DC2 local-storage dense-c |
| `redshift-data-api-deployer` | deploy | Deploys AWS Redshift Data API configurations with production defaults: query execution without persistent connection (ExecuteStatement, BatchExecuteSt |
| `redshift-query-troubleshooter` | troubleshoot | Diagnoses Amazon Redshift query failures through a twelve-category diagnostic tree: WLM queue timeout (queue wait vs execution time), table lock detec |
| `redshift-serverless-deployer` | deploy | Deploys Amazon Redshift Serverless with production-grade configuration: namespace creation (DB name, admin credentials, KMS encryption, IAM roles, VPC |
| `redshift-wlm-optimizer` | optimize | Optimises Amazon Redshift Workload Management (WLM) across eleven dimensions: WLM queue configuration (auto vs manual WLM with static concurrency slot |
