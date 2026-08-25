# Diagnostic Commands (load on demand) — Amazon DataZone Domain Deployer

Domain-creation and data-source-connection CLI listings moved verbatim
from SKILL.md. Loaded on demand.

---

## Step 1 — domain creation command (moved from SKILL.md)



```bash
# Create a DataZone domain
DOMAIN_ID=$(aws datazone create-domain \
  --name analytics-domain \
  --description "Centralized data governance domain for analytics" \
  --domain-execution-role arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution \
  --kms-key-id alias/datazone-cmk \
  --region us-east-1 \
  --query 'id' --output text)

echo "Domain ID: $DOMAIN_ID"
```



## Step 1 — verify domain status command (moved from SKILL.md)



**Verify the domain is AVAILABLE:**

```bash
aws datazone get-domain \
  --domain-id "$DOMAIN_ID" \
  --query 'status' --region us-east-1
# Expected: AVAILABLE
```



## Step 3 — data source connection commands (S3, Redshift, RDS) (moved from SKILL.md)



### S3 data source

```bash
# Create an S3 data source in the project
aws datazone create-data-source \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --name customer-events-s3 \
  --type S3 \
  --connection-id "$(aws datazone create-connection \
    --domain-id "$DOMAIN_ID" \
    --project-id "$PROJECT_ID" \
    --name customer-s3-connection \
    --type S3 \
    --s3 '{
      "location": {
        "bucketName": "my-customer-events",
        "key": "events/"
      },
      "roleArn": "arn:aws:iam::222222222222:role/DataZoneS3AccessRole"
    }' \
    --query 'id' --output text)" \
  --region us-east-1
```

### Redshift data source

```bash
# Create a Redshift data source
aws datazone create-data-source \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --name sales-dw-redshift \
  --type REDSHIFT \
  --connection-id "$(aws datazone create-connection \
    --domain-id "$DOMAIN_ID" \
    --project-id "$PROJECT_ID" \
    --name sales-redshift-connection \
    --type REDSHIFT \
    --redshift '{
      "clusterId": "sales-dw-cluster",
      "databaseName": "sales_db",
      "credentials": {
        "secretArn": "arn:aws:secretsmanager:us-east-1:222222222222:secret:redshift-creds-xxx"
      },
      "roleArn": "arn:aws:iam::222222222222:role/DataZoneRedshiftAccessRole"
    }' \
    --query 'id' --output text)" \
  --region us-east-1
```

### RDS data source

```bash
# Create an RDS data source
aws datazone create-data-source \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --name orders-rds \
  --type RDS \
  --connection-id "$(aws datazone create-connection \
    --domain-id "$DOMAIN_ID" \
    --project-id "$PROJECT_ID" \
    --name orders-rds-connection \
    --type RDS \
    --rds '{
      "instanceId": "orders-db",
      "databaseName": "orders",
      "credentials": {
        "secretArn": "arn:aws:secretsmanager:us-east-1:222222222222:secret:rds-creds-xxx"
      },
      "roleArn": "arn:aws:iam::222222222222:role/DataZoneRDSAccessRole"
    }' \
    --query 'id' --output text)" \
  --region us-east-1
```


