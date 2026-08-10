# End-to-End Example: OpenSearch Domain Deployment

A walkthrough showing how to use the `opensearch-domain-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production managed OpenSearch cluster for a
search application. The domain needs:

- Managed cluster (full feature set, predictable steady-state workload)
- 6 data nodes (r6g.2xlarge.search) across 3 AZs (Multi-AZ)
- 3 dedicated master nodes (c6g.large.search) — latency-sensitive
- EBS gp3 100GB per node (~510 GB usable at the 85% free-space watermark)
- Customer-managed CMK for encryption at rest (alias/prod-opensearch-kms)
- TLS in transit enforced (TLS 1.2 minimum)
- VPC-only access (subnets subnet-0aaa/0bbb/0ccc, SG sg-search123 port 443)
- FGAC with IAM master user (arn:aws:iam::123456789012:role/opensearch-master)
- 30-50 GB per shard (17 shards for ~500 GB indices)
- Replica count: 1 (Multi-AZ places replica in different AZ)
- Automated snapshots: 14 day retention
- Engine: OpenSearch 2.11

Domain name: `prod-search`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-opensearch-domain
```

Then paste the requirements.

### Option B: Natural language

```
You: "Provision a production OpenSearch Service domain named prod-search in
      us-east-1. Search application, ~500 GB indices, latency-sensitive.
      Managed cluster with 6 data nodes (r6g.2xlarge.search) Multi-AZ
      with 3 dedicated masters. EBS gp3 100GB per node. Customer CMK
      alias/prod-opensearch-kms. VPC-only — subnets subnet-0aaa/0bbb/0ccc,
      SG sg-search123 inbound 443 from sg-app456. FGAC with IAM master
      user role opensearch-master. Snapshots 14 days. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an opensearch domain"
```

Output:

```
[Phase: Deploy | Skills routed: opensearch-domain-deployer]

Primary route: opensearch-domain-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
DOMAIN: prod-search
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Deployment type: managed cluster
  [✓] Instance type: r6g.2xlarge.search (data nodes)
  [✓] Instance count: 6 data nodes (2 per AZ × 3 AZs)
  [✓] Multi-AZ (3-zone): Enabled (us-east-1a/b/c)
  [✓] Dedicated master nodes: 3 × c6g.large.search
  [✓] Storage: EBS gp3 100GB per node (600 GB cluster capacity; ~510 GB usable)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-opensearch-kms)
  [✓] Encryption in transit (TLS): Enabled (Policy-Min-TLS-1-2-2019-07)
  [✓] Network access: VPC-only (subnets: subnet-0aaa/0bbb/0ccc, SG: sg-search123 port 443)
  [✓] Fine-grained access control (FGAC): IAM master user
  [✓] Shard count rule: 30-50 GB per shard applied (17 shards for 500 GB indices)
  [✓] Replica count: 1 (Multi-AZ places replica in different AZ)
  [✓] Automated snapshots: Enabled (retention 14 days)
  [✓] UltraWarm: Disabled (workload is search, not time-series)
  [✓] Cold storage: Disabled
  [✓] OpenSearch Serverless: No
VERIFICATION_COMMANDS:
  aws opensearch describe-domain --domain-name prod-search
  aws opensearch describe-domain-config --domain-name prod-search
  aws ec2 describe-security-groups --group-ids sg-search123
  aws kms describe-key --key-id alias/prod-opensearch-kms
  aws iam get-role --role-name opensearch-master
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# Step 1: Create the security group (inbound 443 from application SG)
aws ec2 create-security-group \
  --group-name opensearch-prod-sg \
  --description "Security group for prod OpenSearch domain" \
  --vpc-id vpc-0aaa

aws ec2 authorize-security-group-ingress \
  --group-id sg-search123 \
  --protocol tcp \
  --port 443 \
  --source-security-group-id sg-app456

# Step 2: Create the OpenSearch domain
aws opensearch create-domain \
  --domain-name prod-search \
  --engine-version OpenSearch_2.11 \
  --cluster-config \
    InstanceType=r6g.2xlarge.search,InstanceCount=6,\
DedicatedMasterEnabled=true,DedicatedMasterType=c6g.large.search,DedicatedMasterCount=3,\
ZoneAwarenessEnabled=true,ZoneAwarenessConfig={AvailabilityZoneCount=3} \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=100 \
  --encryption-at-rest-options \
    Enabled=true,KmsKeyId=arn:aws:kms:us-east-1:123456789012:alias/prod-opensearch-kms \
  --node-to-node-encryption-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true,TLSSecurityPolicy=Policy-Min-TLS-1-2-2019-07 \
  --advanced-security-options \
    Enabled=true,InternalUserDatabaseEnabled=false,\
MasterUserOptions={MasterUserARN=arn:aws:iam::123456789012:role/opensearch-master} \
  --vpc-options SubnetIds=subnet-0aaa,subnet-0bbb,subnet-0ccc,SecurityGroupIds=sg-search123 \
  --snapshot-options AutomatedSnapshotStartHour=3 \
  --tags Key=Environment,Value=production Key=Workload,Value=search

# Step 3: Wait for the domain to become active (10-30 minutes)
aws opensearch describe-domain --domain-name prod-search \
  --query 'DomainStatus.[Processing,Endpoint]'

# Step 4: CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-search-cluster-status-red" \
  --namespace AWS/ES \
  --metric-name ClusterStatus.red \
  --dimensions Name=DomainName,Value=prod-search Name=ClientId,Value=123456789012 \
  --statistic Maximum --period 60 --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:opensearch-alerts

aws cloudwatch put-metric-alarm \
  --alarm-name "prod-search-jvm-memory-high" \
  --namespace AWS/ES \
  --metric-name JVMMemoryPressure \
  --dimensions Name=DomainName,Value=prod-search Name=ClientId,Value=123456789012 \
  --statistic Average --period 60 --threshold 85 \
  --comparison-operator GreaterThan --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:opensearch-alerts
```

---

## Step 4 — Post-deployment verification

Run the verification commands from the checklist to confirm every
configuration was applied:

```bash
# Domain config — InstanceType, InstanceCount, MultiAZ, DedicatedMaster,
# EBS, EncryptionAtRest, NodeToNodeEncryption, AdvancedSecurityOptions,
# VPCOptions, SnapshotOptions
aws opensearch describe-domain --domain-name prod-search
aws opensearch describe-domain-config --domain-name prod-search

# Security group — port 443 inbound from sg-app456
aws ec2 describe-security-groups --group-ids sg-search123

# KMS key — KeyState: Enabled, Enabled: true
aws kms describe-key --key-id alias/prod-opensearch-kms

# Master IAM role exists
aws iam get-role --role-name opensearch-master
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Encryption at rest | Forgets (cannot be added later) | Enabled at creation | Adding encryption at rest to an existing domain is NOT supported — requires new domain + reindex. The skill refuses to provision without it. |
| Public vs VPC access | Public with IP allowlist | VPC-only with FGAC | IP allowlist is a network control, not authentication. VPC-only + FGAC + IAM is the production baseline. |
| Multi-AZ node count | 4 data nodes (uneven) | 6 data nodes (multiple of 3) | Multi-AZ (3-zone) requires instance count divisible by 3 for even shard allocation. |
| Dedicated masters | Skipped ("optional") | 3 dedicated masters (mandatory) | For latency-sensitive production with 6 data nodes, dedicated masters prevent cluster-state work from spiking query latency. |
| Shard count | 5 shards per index (default) | 30-50 GB per shard rule | Over-sharding small indices wastes overhead; under-sharding large indices creates hot shards. The skill applies the 30-50 GB rule. |
| JVM heap | "All available memory" | Capped at 31 GB | Above 31 GB, the JVM disables compressed oops — more memory overhead. The skill caps heap even on larger instances. |
| TLS security policy | Defaults to TLS 1.0 allowed | Policy-Min-TLS-1-2-2019-07 | TLS 1.0/1.1 are deprecated and vulnerable. The skill refuses to allow them. |
| FGAC mode | "IP-only is fine" | IAM master user (or Cognito) | IP allowlist is not authentication. The skill refuses IP-only FGAC for production. |
| t3 instance for production | t3.small.search "to save cost" | r6g.2xlarge.search | The t3 family has CPU credits that burst; sustained traffic depletes credits and throttles. The skill refuses t3 for production. |

---

## Related artifacts

- **Skill definition:** `skills/opensearch-domain-deployer/SKILL.md`
- **Topology and indexing guide:** `skills/opensearch-domain-deployer/references/topology-and-indexing.md`
- **Provisioning CLI commands:** `skills/opensearch-domain-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-opensearch-domain.md`
- **Eval suite:** `skills/opensearch-domain-deployer/evals/evals.json`
- **Legacy test cases:** `skills/opensearch-domain-deployer/eval/test-cases.yaml`
