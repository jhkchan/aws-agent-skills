# Schema Design and Encryption — Keyspaces Keyspace Deployer

Deep reference on Cassandra data model for Keyspaces (partition key
cardinality, clustering key sort order, column types, immutability),
encryption (at-rest KMS: AWS-owned vs AWS-managed vs customer-managed,
client-side envelope encryption via KMS), TTL mechanics, PITR
configuration, and CQL connectivity via the Cassandra driver with SigV4.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## Schema design fundamentals

### Partition key: the distribution mechanism

The partition key determines which storage partition holds the data.
Keyspaces hashes the partition key to determine placement.

```text
Single-column partition key:
  PARTITION KEY (user_id)
  → data distributed by hash(user_id)

Composite partition key:
  PARTITION KEY (user_id, event_date)
  → data distributed by hash(user_id, event_date)
  → groups a user's events for a single date into one partition
  → prevents unbounded partition growth (each partition = one day)
```

**Cardinality rules:**

| Partition key | Cardinality | Distribution | Risk |
|---|---|---|---|
| `status` (3 values: ACTIVE, INACTIVE, PENDING) | 3 | ALL data in 3 partitions | EXTREME hotspot risk |
| `category` (100 values) | 100 | Data in 100 partitions | HIGH hotspot risk |
| `user_id` (UUID) | millions | Even distribution | GOOD |
| `device_id` (UUID) | millions | Even distribution | GOOD |
| `(user_id, event_date)` | millions/day | Time-bucketed | BEST for time-series |

**Anti-pattern: low-cardinality partition key.** If the number of
distinct partition key values is small, all data concentrates in a
few partitions, causing hotspots and throttling. Always verify
cardinality before creating the table.

### Clustering key: sort order within a partition

The clustering key determines the sort order of rows WITHIN a
partition. It supports range queries and ordered retrieval.

```text
Single-column clustering key:
  CLUSTERING KEY (event_time DESC)
  → rows sorted newest-first within each partition

Multi-column clustering key:
  CLUSTERING KEY (order_type ASC, order_ts DESC)
  → rows sorted by order_type alphabetically, then by timestamp newest-first
  → supports: WHERE order_type = 'RETURN' AND order_ts >= '2026-08-01'
```

**Clustering key order (ASC/DESC) is fixed at table creation.** It
cannot be changed without dropping and recreating the table.

**Clustering key must match the dominant query pattern:**

| Query pattern | Clustering key |
|---|---|
| "newest 10 events for user X" | `(event_time DESC)` |
| "all returns for customer X on date Y, newest first" | `(order_type ASC, order_ts DESC)` |
| "sensor readings between time A and time B" | `(reading_time ASC)` |
| "products by category, then by price low-to-high" | `(category ASC, price ASC)` |

### Schema immutability

| Property | Mutable after creation? | How to change |
|---|---|---|
| Partition key | NO | Drop table, recreate |
| Clustering key | NO | Drop table, recreate |
| Clustering key order (ASC/DESC) | NO | Drop table, recreate |
| Regular columns | YES — add only | `ALTER TABLE ... ADD COLUMN` |
| Column types | NO (cannot change type) | Drop table, recreate |
| Table name | NO | Drop table, recreate |
| Keyspace name | NO | Drop keyspace, recreate |

**Implication:** partition key and clustering key design is the most
critical decision. Get it right before creating the table. Changing
it means losing all data.

### Column types

| CQL Type | Description | Size |
|---|---|---|
| `ascii` | ASCII string | variable |
| `bigint` | 64-bit signed integer | 8 bytes |
| `blob` | Arbitrary bytes | variable |
| `boolean` | true/false | 1 byte |
| `date` | Date (no time) | 4 bytes |
| `decimal` | Arbitrary precision decimal | variable |
| `double` | 64-bit IEEE float | 8 bytes |
| `float` | 32-bit IEEE float | 4 bytes |
| `inet` | IP address (IPv4 or IPv6) | variable |
| `int` | 32-bit signed integer | 4 bytes |
| `list<T>` | Ordered collection | variable |
| `map<K,V>` | Key-value collection | variable |
| `set<T>` | Unordered unique collection | variable |
| `text` / `varchar` | UTF-8 string | variable |
| `timestamp` | Date + time (ms precision) | 8 bytes |
| `timeuuid` | UUID with timestamp component | 16 bytes |
| `uuid` | UUID | 16 bytes |
| `tinyint` | 8-bit signed integer | 1 byte |
| `varint` | Arbitrary precision integer | variable |

**Note:** Keyspaces does NOT support secondary indexes (unlike
DynamoDB GSIs). All query patterns must be served by the partition
key + clustering key design. If you need a different access pattern,
create a separate table (materialized view pattern).

## Encryption

### Encryption at rest

Keyspaces encrypts all data at rest by default. The key type determines
the level of control:

| Key type | Cost | Rotation | CloudTrail audit | Cross-account |
|---|---|---|---|---|
| AWS-owned key (default) | Free | N/A (AWS manages internally) | No | No |
| AWS-managed key (`aws/cassandra`) | Free | Automatic (yearly) | Yes | No |
| Customer-managed key (CMK) | $1/month + $0.03 per 10K requests | Configurable (annual default) | Yes | Yes |

**Using a customer-managed key (CMK):**

```bash
# Create a CMK
KMS_KEY_ID=$(aws kms create-key \
  --description "Keyspaces encryption key" \
  --query 'KeyMetadata.KeyId' --output text)

# Create an alias for easy reference
aws kms create-alias \
  --alias-name alias/keyspaces-cmk \
  --target-key-id "$KMS_KEY_ID"

# Set the CMK on the table
aws keyspaces create-table \
  --keyspace-name my_keyspace \
  --table-name my_table \
  --schema-definition '{...}' \
  --encryption-spec "{
    \"type\": \"CUSTOMER_MANAGED_KEYS\",
    \"kmsKeyIdentifier\": \"$KMS_KEY_ID\"
  }"
```

**KMS key policy for Keyspaces access:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "cassandra.amazonaws.com"
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

### Client-side envelope encryption

Client-side encryption uses envelope encryption: the application uses
the KMS CMK to generate a data encryption key (DEK), encrypts the
payload locally with the DEK, and stores the encrypted DEK alongside
the ciphertext in Keyspaces.

```text
Client-side encryption flow:
  1. Application calls kms:GenerateDataKey → gets plaintext DEK + encrypted DEK
  2. Application encrypts payload with plaintext DEK (AES-256)
  3. Application stores encrypted DEK + ciphertext in Keyspaces
  4. Application zeroes out plaintext DEK from memory
  5. On read: application calls kms:Decrypt on encrypted DEK → gets plaintext DEK
  6. Application decrypts ciphertext with plaintext DEK
```

**Recommended approach:** use the AWS Encryption SDK, which handles
DEK generation, caching (via the data key caching provider), and
rotation automatically.

```python
# AWS Encryption SDK example
import boto3
from aws_encryption_sdk import EncryptionSDKClient
from aws_encryption_sdk.identifiers import CommitmentPolicy
from aws_encryption_sdk.key_providers.kms import KMSMasterKeyProvider

client = boto3.client('kms', region_name='us-east-1')

# Create the encryption SDK client
encryption_client = EncryptionSDKClient(
    commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_REQUIRE_DECRYPT
)

# Create a KMS master key provider
master_key_provider = KMSMasterKeyProvider(
    key_ids=['arn:aws:kms:us-east-1:123456789012:key/abc123']
)

# Encrypt data
ciphertext, encryptor_header = encryption_client.encrypt(
    source=b'{"ssn": "123-45-6789", "email": "user@example.com"}',
    key_provider=master_key_provider
)

# Store ciphertext in Keyspaces
session.execute(
    "INSERT INTO my_keyspace.pii_records (record_id, pii_data) VALUES (?, ?)",
    (record_id, ciphertext)
)

# Decrypt data
plaintext, decryptor_header = encryption_client.decrypt(
    source=ciphertext,
    key_provider=master_key_provider
)
```

**Critical limitation:** WHERE clauses on encrypted columns do NOT
work. Keyspaces sees ciphertext, so `WHERE pii_data = 'something'`
compares ciphertext bytes, not plaintext. Design the schema so
encrypted columns are never used in WHERE clauses or range scans.

## TTL (time-to-live)

TTL causes rows to auto-expire after a specified number of seconds.

```sql
-- Per-row TTL at insert time (row expires after 86400 seconds = 24 hours)
INSERT INTO my_keyspace.user_events
  (user_id, event_date, event_time, event_type)
VALUES (uuid(), '2026-08-05', toTimestamp(now()), 'LOGIN')
USING TTL 86400;

-- Default TTL for the table (applied to all rows unless overridden)
ALTER TABLE my_keyspace.user_events
WITH default_time_to_live = 604800;  -- 7 days

-- Per-column TTL is NOT supported in Cassandra/Keyspaces
-- TTL applies to the entire row, not individual columns
```

**TTL behavior:**
- Expired rows are marked for deletion and removed during compaction
  (not immediately).
- TTL queries (`SELECT TTL(event_type) FROM ...`) show the remaining
  TTL for each row.
- Setting TTL = 0 removes the TTL (row persists indefinitely).
- TTL is specified in seconds.

## Point-in-time recovery (PITR)

PITR provides continuous backup of the last 35 days. It is DISABLED by
default.

```bash
# Enable PITR
aws keyspaces update-table \
  --keyspace-name my_keyspace \
  --table-name my_table \
  --point-in-time-recovery-enabled

# Check PITR status
aws keyspaces get-table \
  --keyspace-name my_keyspace \
  --table-name my_table \
  --query 'pointInTimeRecovery' --output json
```

**PITR characteristics:**
- Recovery window: last 35 days (continuous, not snapshots).
- Earliest restorable time: 5 minutes after PITR was enabled.
- Restore creates a NEW table (does not overwrite the original).
- Restore time: proportional to table size (minutes to hours).
- Cost: billed based on backup storage size.

## CQL connectivity via Cassandra driver

### Prerequisites

- DataStax `cassandra-driver` (Python) or equivalent for Java/Node/Go.
- SSL/TLS with AmazonRootCA1.pem certificate.
- SigV4 authentication (IAM credentials, not passwords).
- Port 9142 (NOT 9042).

### Python connectivity example

```python
from cassandra.cluster import Cluster
from cassandra.sigv4.auth import SigV4AuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2, CERT_REQUIRED
import boto3

# SSL context with Amazon Root CA
ssl_context = SSLContext(PROTOCOL_TLSv1_2)
ssl_context.load_verify_locations('/path/to/AmazonRootCA1.pem')
ssl_context.verify_mode = CERT_REQUIRED
ssl_context.check_hostname = True

# SigV4 auth provider with IAM credentials
session_credentials = boto3.Session().get_credentials()
auth_provider = SigV4AuthProvider(
    credentials=session_credentials,
    region_name='us-east-1'
)

# Connect to Keyspaces
cluster = Cluster(
    ['cassandra.us-east-1.amazonaws.com'],
    port=9142,
    ssl_context=ssl_context,
    auth_provider=auth_provider,
    protocol_version=4,
    load_balancing_policy=DCAwareRoundRobinPolicy(local_dc='us-east-1'),
    execution_profiles={
        'default': ExecutionProfile(
            request_timeout=10,
            consistency=ConsistencyLevel.LOCAL_QUORUM
        )
    }
)

session = cluster.connect()
session.execute("SELECT * FROM my_keyspace.user_events LIMIT 10")
```

### Required IAM permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cassandra:Select",
        "cassandra:Modify"
      ],
      "Resource": [
        "arn:aws:cassandra:us-east-1:123456789012:/keyspace/my_keyspace/table/*"
      ]
    }
  ]
}
```

**Consistency:** Keyspaces supports `LOCAL_QUORUM` (default), `LOCAL_ONE`,
and `ALL` consistency levels. It does NOT support `QUORUM` or `EACH_QUORUM`
(these are multi-datacenter levels that don't apply to Keyspaces'
single-region model).

### Downloading the Amazon Root CA certificate

```bash
# Download the Amazon Root CA certificate
curl https://www.amazontrust.com/repository/AmazonRootCA1.pem -o AmazonRootCA1.pem

# Verify the certificate fingerprint
openssl x509 -in AmazonRootCA1.pem -fingerprint -sha256 -noout
```
