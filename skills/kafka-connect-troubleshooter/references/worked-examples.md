# Worked examples — kafka-connect-troubleshooter

Secondary worked examples, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Worked example — IAM auth missing on MSK (moved from SKILL.md)

```text
TARGET: postgres-source-connector
VERDICT: ROOT_CAUSE_FOUND
REASON: Connector cannot produce to MSK; logs show SASL_NOT_LOGGED_IN.
  MSK ClientAuthentication.Sasl.Iam is disabled; connector uses sasl.iam.
CATEGORY: IAM_AUTH
EVIDENCE:
  - connector FAILED, tasks[0] FAILED
  - CloudWatch: "ClusterAuthorizationException: SASL_NOT_LOGGED_IN"
  - Failing probe:
    aws kafka describe-cluster --cluster-arn $CLUSTER_ARN
      --query 'ClusterInfo.ClientAuthentication.Sasl'
    → returns {} (Iam not enabled)
  - Passing probes: SG egress to 9094 OK; role has kafka-cluster:* Allow
REMEDIATION:
  1. Enable IAM auth via cluster configuration update:
     aws kafka update-configuration --cluster-arn $CLUSTER_ARN \
       --configuration-info '{"RevisionId":2,"Arn":"<config-arn>"}'
  2. Wait for APPLY_CONFIGURATION (~10-15 min).
  3. Restart the connector.
```

## Worked example — source lag with hot partition (moved from SKILL.md)

```text
TARGET: events-stream-source
VERDICT: ROOT_CAUSE_FOUND
REASON: LagMax grows on partition 7 only. Producer key-based
  partitioner concentrates 60% of records ("ACME-001") on
  partition 7; throughput is bottlenecked on one task.
CATEGORY: SOURCE_LAG
EVIDENCE:
  - LagMax=480,000 on partition 7; <2,000 on others
  - Partition 7 task: 5 records/s vs 200/s on others
  - Passing probes: no rebalance; source DB healthy
REMEDIATION:
  1. Salt the producer's hot key: key = original + ":" + (rand() % 8)
  2. OR raise connector tasks.max to match partition count (default 1).
  3. Deploy and verify LagMax falls over 10 minutes.
```

## Worked example — plugin missing (Debezium) (moved from SKILL.md)

```text
TARGET: debezium-mysql-source
VERDICT: ROOT_CAUSE_FOUND
REASON: Connector fails on creation with ClassNotFoundException.
  Custom plugin ARN references a fat JAR missing the Debezium MySQL
  module; plugin state is FAILED.
CATEGORY: PLUGIN_MISSING
EVIDENCE:
  - connector FAILED, no tasks running
  - CloudWatch: "ClassNotFoundException:
    io.debezium.connector.mysql.MySqlConnector"
  - Failing probe:
    aws kafkaconnect describe-custom-plugin --custom-plugin-arn $ARN
    → state=FAILED, "missing manifest dependencies"
  - Passing probes: connector.class matches intended class; MSK reachable
REMEDIATION:
  1. Build a complete Debezium plugin ZIP:
     unzip debezium-connector-mysql-2.5.tar.gz
     zip -r debezium-plugin.zip debezium-connector-mysql
     aws s3 cp debezium-plugin.zip s3://plugins/
  2. Create new plugin:
     aws kafkaconnect create-custom-plugin \
       --content-location s3://plugins/debezium-plugin.zip \
       --content-type ZIP --name debezium-mysql-2.5
  3. Recreate the connector referencing the new plugin ARN.
```

## Worked example — NEED_MORE_INFO (moved from SKILL.md)

```text
TARGET: jdbc-sink-connector
VERDICT: NEED_MORE_INFO
REASON: Connector state=FAILED, trace empty, and CloudWatch logging
  is not configured. Cannot determine the failing category without
  logs.
CATEGORY: UNKNOWN
EVIDENCE:
  - connector FAILED, tasks[0] FAILED, trace=""
  - aws logs describe-log-groups --log-group-name-prefix
    /aws/kafkaconnect/jdbc-sink → empty
  - Plugin ACTIVE; MSK reachable
REMEDIATION:
  1. Update the connector with log delivery:
     aws kafkaconnect update-connector --connector-arn $ARN \
       --log-delivery '{"workerLogDelivery":{"cloudWatchLogs":{"enabled":true,"logGroup":"/aws/kafkaconnect/jdbc-sink"}}}'
  2. Wait for the connector to fail again (or trigger a restart).
  3. Re-invoke this skill with the new logs available.
```
