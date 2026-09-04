# Storage skills (40)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `backup-audit-automator` | automate | Automates AWS Backup audit and compliance reporting with production defaults: backup report plan creation (daily/weekly compliance reports), report te |
| `backup-compliance-automator` | automate | Designs AWS Backup compliance automation across the four pillars: AWS Backup Audit Manager (audit framework, audit template, manual and automated cont |
| `backup-cross-region-operator` | operate | Operates AWS Backup cross-region and cross-account operations — adds cross-region copy rules to backup plans (destination region, KMS, lifecycle), con |
| `backup-plan-auditor` | audit | Audits AWS Backup plans for coverage gaps (empty or missing resource selections), vault risks (missing vault lock, governance-mode lock, AWS-managed e |
| `backup-schedule-automator` | automate | Designs and implements automated AWS Backup scheduling workflows using backup plans, tag-based resource assignment, cross-account backup via Organizat |
| `backup-vault-compliance-automator` | automate | Designs and implements AWS Backup vault compliance automation workflows. |
| `backup-vault-deployer` | deploy | Provisions AWS Backup vaults with production defaults: vault creation (KMS encryption, tags), backup plans (rule-based with lifecycle, schedule, cross |
| `backup-vault-operator` | operate | Operates AWS Backup vault lifecycles — creates vaults with KMS encryption and tags, applies vault locks (compliance WORM vs governance soft lock with  |
| `datasync-task-operator` | operate | Operates AWS DataSync task end-to-end — agent deployment (on-prem VM, EC2), location configuration for every supported source (NFS, SMB, S3, HDFS, Obj |
| `dlm-lifecycle-policy-auditor` | audit | Audits AWS Data Lifecycle Manager (DLM) EBS snapshot lifecycle policies for coverage gaps and silent-failure modes: disabled policies, empty tag/resou |
| `ebs-volume-auditor` | audit | Audits AWS EBS volumes and EBS snapshots for unencrypted volumes, unattached cost-drift volumes, legacy gp2 volume types (gp3 upgrade path), stale sna |
| `ebs-volume-optimizer` | optimize | Optimises EBS volume cost across six dimensions: volume type migration (gp2 to gp3 is 20% cheaper with higher baseline IOPS; io1/io2 to gp3 when provi |
| `ecr-repository-auditor` | audit | Audits AWS ECR private repositories for public-access exposure via repositoryPolicy, image-scan configuration gaps (scanOnPush off + unscanned images) |
| `efs-access-point-deployer` | deploy | Provisions EFS Access Points and dependent primitives with production defaults: root-directory auto-creation, POSIX user identity (uid, gid, secondary |
| `efs-filesystem-auditor` | audit | Audits AWS EFS filesystems for encryption-at-rest, filesystem policy public principal exposure, encryption-in-transit enforcement, lifecycle managemen |
| `fsx-filesystem-deployer` | deploy | Provisions Amazon FSx file systems with production defaults: FSx for Windows (storage type SSD/HDD, throughput capacity, deployment Multi-AZ/Single-AZ |
| `s3-access-denied-troubleshooter` | troubleshoot | Diagnoses Amazon S3 Access Denied errors through a thirteen-category diagnostic tree: explicit deny in bucket policy overriding an IAM allow, object o |
| `s3-access-points-deployer` | deploy | Provisions S3 Access Points and dependent primitives with production defaults: network-origin selection (Internet vs VPC), VPC endpoint + private DNS, |
| `s3-access-troubleshooter` | troubleshoot | Diagnoses AWS S3 access failures via a systematic six-symptom diagnostic decision tree covering 403 Access Denied on GetObject (object ARN vs bucket A |
| `s3-batch-operations-operator` | operate | Operates S3 Batch Operations at scale — job creation across operation types (copy, replace tag, restore from Glacier, replicate, invoke Lambda, put AC |
| `s3-bucket-policy-deployer` | deploy | Provisions S3 bucket policies with production defaults: policy structure (Principal, Action, Resource, Condition), common patterns (HTTPS-only via aws |
| `s3-directory-bucket-deployer` | deploy | Provisions S3 Express One Zone directory buckets and S3 Tables table buckets with production defaults: directory bucket name format (base-name--az-id- |
| `s3-glacier-restore-operator` | operate | Operates S3 Glacier restore workflows — initiates object restores from Flexible Retrieval tiers (Expedited 1-5 min, Standard 3-5 hr, Bulk 5-12 hr) and |
| `s3-intelligent-tiering-optimizer` | optimize | Optimises S3 storage cost with Intelligent-Tiering: enables bucket-level IntelligentTieringConfiguration, tunes the Archive Access (90-day) and Deep A |
| `s3-lifecycle-automator` | automate | Designs and implements automated S3 lifecycle policy deployment across single and multi-account environments. |
| `s3-lifecycle-optimizer` | optimize | Optimises S3 storage cost through lifecycle-policy design, storage-class selection, and access-pattern analysis. |
| `s3-object-lambda-deployer` | deploy | Provisions S3 Object Lambda Access Points and the supporting transform Lambda function with production defaults: standard Access Point creation, Lambd |
| `s3-outposts-deployer` | deploy | Provisions Amazon S3 on Outposts with production defaults: S3 outpost bucket creation, endpoint (required for accessing S3 on Outpost from on-prem via |
| `s3-performance-optimizer` | optimize | Optimises Amazon S3 performance across eleven dimensions: prefix distribution for partition allocation (auto-scale post-2018/2023), S3 Transfer Accele |
| `s3-public-access-auditor` | audit | Audits S3 bucket configurations (Block Public Access settings, ACLs, bucket policies, Access Points, and Object Ownership) to determine which buckets  |
| `s3-replication-operator` | operate | Operates S3 cross-region replication (CRR) and same-region replication (SRR) end-to-end — rule configuration (priority, filter prefix/tags, status), s |
| `s3-secure-bucket-deployer` | deploy | Provisions S3 buckets with production-grade security defaults: Block Public Access (account + bucket, all 4 settings), default encryption (SSE-S3 or S |
| `s3-storage-class-optimizer` | optimize | Optimises S3 storage cost across six dimensions: lifecycle policy configuration (Standard to Standard-IA to Glacier Instant to Glacier Flexible to Gla |
| `s3-table-bucket-deployer` | deploy | Provisions Amazon S3 Tables (table buckets) with production defaults: table bucket creation (create-table-bucket), namespace management (create-namesp |
| `s3-transfer-acceleration-operator` | operate | Operates S3 Transfer Acceleration workflows — enable/disable acceleration per bucket (put-bucket-accelerate-configuration), cost analysis by source re |
| `s3-version-cleanup-operator` | operate | Operates S3 version cleanup for cost optimization and compliance — NoncurrentVersionExpiration, NoncurrentVersionTransition, NewerNoncurrentVersions,  |
| `storage-gateway-deployer` | deploy | Deploys AWS Storage Gateway with production defaults: gateway types (S3 File Gateway, FSx File Gateway, Volume Gateway cached/stored, Tape Gateway), g |
| `transfer-cost-optimizer` | optimize | Optimises AWS Transfer Family cost across eight dimensions: server endpoint type (PUBLIC vs VPC vs VPC_ENDPOINT — PUBLIC is cheapest with no VPC/NAT c |
| `transfer-family-deployer` | deploy | Provisions AWS Transfer Family servers with secure defaults — SFTP, FTPS, and FTP protocols, server endpoint types (public vs VPC vs VPC_ENDPOINT), id |
| `transfer-family-workflow-deployer` | deploy | Provisions AWS Transfer Family servers and managed workflows with production defaults: SFTP/FTPS/FTP protocol, identity provider (service-managed, AWS |
