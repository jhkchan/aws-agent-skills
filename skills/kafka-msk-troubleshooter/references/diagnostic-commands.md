# MSK Diagnostic Commands — Reference

Supplementary reference for the Kafka MSK Troubleshooter skill. The canonical
command script per failure category, with sample outputs and interpretation.

## Universal first commands (run for any MSK failure)

```bash
# 1. Cluster state + StateInfo
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.{State:State,StateInfo:StateInfo,Version:CurrentBrokerSoftwareInfo.KafkaVersion,Type:CurrentBrokerSoftwareInfo.KafkaVersion}'

# 2. Broker nodes (provisioned only)
aws kafka list-nodes --cluster-arn <arn> \
  --query 'NodeInfoList[*].{Broker:BrokerNodeInfo.BrokerId,Instance:BrokerNodeInfo.InstanceType,Size:BrokerNodeInfo.BrokerVolumeSizeGB,AZ:BrokerNodeInfo.ClientSubnet}'

# 3. Bootstrap brokers
aws kafka get-bootstrap-brokers --cluster-arn <arn>

# 4. Client authentication config
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.ClientAuthentication' --output json
```

Key `State` values:

- `ACTIVE` — cluster healthy
- `HEALTH_ISSUE` — broker-level degradation (check StateInfo for details)
- `CREATING` / `UPDATING` — provisioning or configuration change in progress
- `MAINTENANCE` — AWS-initiated broker replacement or maintenance
- `DELETING` — cluster being deleted

## Per-category command scripts

### Category A: BROKER_FAILURE

```bash
# Cluster state:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.{State:State,StateInfo:StateInfo}'

# Per-broker health:
aws kafka list-nodes --cluster-arn <arn>

# Cluster Tier v2:
aws kafka describe-cluster-v2 --cluster-arn <arn> \
  --query 'ClusterInfo.{Type:ClusterType,State:State,StateInfo:StateInfo}'

# CPU per broker:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name CpuUser \
  --dimensions Name=Cluster Name,Value=<cluster> Name=Broker ID,Value=<id> \
  --start-time $(date -u -d '1 hour ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output text

# Memory per broker:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name MemoryUsed \
  --dimensions Name=Cluster Name,Value=<cluster> Name=Broker ID,Value=<id> \
  --start-time $(date -u -d '1 hour ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output text

# Disk per broker:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name DiskUsage \
  --dimensions Name=Cluster Name,Value=<cluster> Name=Broker ID,Value=<id> \
  --start-time $(date -u -d '24 hours ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output text
```

**Interpretation:**

- `State=HEALTH_ISSUE` + StateInfo mentions broker `NOT_HEALTHY` = broker
  degraded. Check DiskUsage and CpuUser.
- `State=MAINTENANCE` = AWS replacing broker. Wait for `State=ACTIVE`.
- `CpuUser > 85%` sustained = CPU saturated. Check for partition skew.
- `DiskUsage > 90%` = storage issue (see Category G).

### Category B: TOPIC_ISSUE

```bash
# All under-replicated partitions:
kafka-topics --bootstrap-server <bs> --describe --under-replicated-partitions

# Partitions under min ISR:
kafka-topics --bootstrap-server <bs> --describe --under-min-isr-partitions

# Full topic describe:
kafka-topics --bootstrap-server <bs> --describe --topic <topic>

# Offline partitions (cluster-level metric):
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name OfflinePartitions \
  --dimensions Name=Cluster Name,Value=<cluster> \
  --start-time $(date -u -d '1 hour ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum,Maximum --output text

# URP trend:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name UnderReplicatedPartitions \
  --dimensions Name=Cluster Name,Value=<cluster> \
  --start-time $(date -u -d '24 hours ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum,Average,Maximum --output text

# Partition leader distribution (to detect skew):
kafka-topics --bootstrap-server <bs> --describe | \
  awk '{print $6}' | sort | uniq -c | sort -rn

# Trigger preferred replica election:
kafka-preferred-replica-election --bootstrap-server <bs>
```

**Interpretation:**

- `Isr` column shows fewer brokers than `Replicas` = URP. The missing
  brokers are the lagging followers.
- `OfflinePartitions > 0` = P0. All replicas down or ISR below min.
- Intermittent URP during burst = `replica.lag.time.max.ms` too low.
- Leader concentrated on one broker = partition skew.

### Category C: CONNECTIVITY

```bash
# Bootstrap brokers (all endpoint types):
aws kafka get-bootstrap-brokers --cluster-arn <arn> --output json

# Client auth config:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.ClientAuthentication' --output json

# Broker security groups:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.BrokerNodeGroupInfo.SecurityGroups' --output text

# SG inbound rules on brokers:
aws ec2 describe-security-groups --group-ids <broker-sg-id> \
  --query 'SecurityGroups[0].IpPermissions[*].{Port:FromPort,Proto:IpProtocol,Source:UserIdGroupPairs,CIDR:IpRanges}' \
  --output table

# SCRAM secrets:
aws kafka list-scram-secrets --cluster-arn <arn>

# Verify SCRAM secret:
aws secretsmanager describe-secret --secret-id AmazonMSK_<cluster>_credentials

# Test TLS connectivity:
openssl s_client -connect <broker-dns>:9094 -servername <broker-dns>

# Test port reachability:
nc -zv <broker-dns> 9094

# Check ACLs:
kafka-acls --bootstrap-server <bs> --list --topic <topic>
```

**Interpretation:**

- `TimeoutException` = SG blocking port or wrong endpoint. Check SG rules
  for the correct port (9094 TLS, 9096 SCRAM, 9098 IAM).
- `SSLHandshakeException` = client truststore missing the AWS private CA
  cert. Import the CA cert into the client truststore.
- `SASL_AUTHENTICATION_FAILED` (SCRAM) = wrong secret, SCRAM not enabled,
  or secret not associated with cluster.
- `SASL_AUTHENTICATION_FAILED` (IAM) = IAM policy missing
  `kafka-cluster:Connect` on the cluster ARN.

### Category D: ZOOKEEPER

```bash
# Verify ZK vs KRaft mode:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.CurrentBrokerSoftwareInfo'

# ZK latency:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name ZooKeeperRequestLatencyMs \
  --dimensions Name=Cluster Name,Value=<cluster> Name=Broker ID,Value=<id> \
  --start-time $(date -u -d '1 hour ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output text

# ZK-related config:
aws kafka describe-configuration --arn <config-arn> \
  --query 'Configuration.ServerProperties' --output text | base64 --decode \
  | grep -E "zookeeper|ssl"

# Broker logs for ZK errors:
aws logs filter-log-events \
  --log-group-name /aws/kafka/<cluster>/broker-<id> \
  --filter-pattern "ZooKeeper session expired" \
  --start-time <epoch-ms> --end-time <epoch-ms>
```

### Category E: CONFIGURATION

```bash
# Read the MSK configuration:
aws kafka describe-configuration --arn <config-arn> \
  --query 'Configuration.ServerProperties' --output text | base64 --decode

# List configuration revisions:
aws kafka describe-configuration-revisions --arn <config-arn>

# Topic-level overrides:
kafka-configs --bootstrap-server <bs> \
  --entity-type topics --entity-name <topic> --describe

# Broker-level overrides:
kafka-configs --bootstrap-server <bs> \
  --entity-type brokers --entity-name <id> --describe

# Create a new configuration revision:
aws kafka create-configuration \
  --name "<config-name>" \
  --server-properties file://updated.properties \
  --kafka-versions "3.5.1"

# Apply configuration to cluster:
aws kafka update-cluster-configuration \
  --cluster-arn <arn> \
  --configuration-info file://config-info.json \
  --current-version <current-cluster-version>
```

### Category F: MONITORING

```bash
# Check monitoring config:
aws kafka describe-monitoring --cluster-arn <arn>

# Check log delivery:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.LoggingInfo'

# Verify CloudWatch log groups:
aws logs describe-log-groups \
  --log-group-name-prefix /aws/kafka/<cluster>

# Verify metrics exist:
aws cloudwatch list-metrics \
  --namespace AWS/Kafka \
  --dimensions Name=Cluster Name,Value=<cluster> \
  --query 'Metrics[*].MetricName'

# Enable enhanced monitoring:
aws kafka update-monitoring \
  --cluster-arn <arn> \
  --current-version <version> \
  --enhanced-monitoring PER_BROKER

# Enable open monitoring (Prometheus JMX):
aws kafka update-monitoring \
  --cluster-arn <arn> \
  --current-version <version> \
  --open-monitoring '{"Prometheus":{"JmxExporter":{"EnabledInBroker":true}}}'
```

### Category G: STORAGE

```bash
# Disk usage per broker:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name DiskUsage \
  --dimensions Name=Cluster Name,Value=<cluster> Name=Broker ID,Value=<id> \
  --start-time $(date -u -d '7 days ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output text

# Per-broker disk usage via kafka-log-dirs:
kafka-log-dirs --bootstrap-server <bs> \
  --describe --topic-list <topic1>,<topic2> \
  --command-config <client-props>

# Topic retention settings:
kafka-configs --bootstrap-server <bs> \
  --entity-type topics --entity-name <topic> --describe \
  | grep -E "retention|cleanup|segment"

# Broker volume size:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.BrokerNodeGroupInfo.StorageInfo' --output json
```

## Combining signals — the diagnostic trinity

```bash
# 1. CLUSTER STATE
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.{State:State,StateInfo:StateInfo}'

# 2. PARTITION HEALTH
kafka-topics --bootstrap-server <bs> --describe --under-replicated-partitions

# 3. CLOUDWATCH METRICS
for METRIC in UnderReplicatedPartitions OfflinePartitions CpuUser DiskUsage BytesInPerSec; do
  echo "=== $METRIC ==="
  aws cloudwatch get-metric-statistics \
    --namespace AWS/Kafka --metric-name $METRIC \
    --dimensions Name="Cluster Name",Value=<cluster> \
    --start-time $(date -u -d '1 hour ago' +%FT%TZ) \
    --end-time $(date -u +%FT%TZ) \
    --period 300 --statistics Average,Maximum --output text
done
```

## Output verification commands

After applying a fix:

```bash
# Verify URP is resolved:
kafka-topics --bootstrap-server <bs> --describe --under-replicated-partitions
# Should return empty after the fix takes effect.

# Verify cluster State returned to ACTIVE:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.{State:State,StateInfo:StateInfo}'

# Verify producer/consumer connectivity:
kafka-console-producer --bootstrap-server <bs> --topic <test-topic> \
  --producer.config <client-props>
kafka-console-consumer --bootstrap-server <bs> --topic <test-topic> \
  --consumer.config <client-props> --from-beginning

# Verify DiskUsage is decreasing after retention fix:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name DiskUsage \
  --dimensions Name=Cluster Name,Value=<cluster> Name=Broker ID,Value=1 \
  --start-time $(date -u -d '6 hours ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average --output text

# Verify configuration applied:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.CurrentBrokerSoftwareInfo.ConfigurationInfo'
```
