# Secrets Manager Rotation Lambda Templates Reference

Load this reference when planning or executing a rotation Lambda setup.
The templates below cover the canonical rotation function structure, the
AWS-managed templates by secret type, and the IAM permissions each template
requires.

## Four-step rotation contract

Every rotation Lambda — managed or custom — must implement four handler
entry points. Secrets Manager calls the Lambda four times per rotation,
once per step, passing `event['Step']` to indicate which handler to run.

| Step | Handler | Action | Failure footprint |
|---|---|---|---|
| `createSecret` | Generate new credential; `PutSecretValue` with `AWSPENDING` stage | New version created in `AWSPENDING`. Target untouched. | KMS disabled, `PutSecretValue` denied, or invalid chars in generated password |
| `setSecret` | Apply `AWSPENDING` credential to the target (DB `ALTER USER`, API `PUT /credential`) | Target now accepts the new credential. `AWSCURRENT` still serves the old. | Target unreachable, `AWSCURRENT` no longer matches (manual change), or new credential rejected |
| `testSecret` | Log in to target with `AWSPENDING` credential; verify it works | Read-only validation. No state change. | Race with `setSecret`, connection limit, login timeout |
| `finishSecret` | `UpdateSecretVersionStage` to move `AWSCURRENT` to new version | Applications now read the new credential. Old version moves to `AWSPREVIOUS`. | `UpdateSecretVersionStage` permission denied |

A stuck `AWSPENDING` version is the forensic signature of a failure at
`setSecret` or `testSecret`. The new credential may or may not be live on
the target depending on whether `setSecret` completed.

## AWS-managed rotation templates

| Secret type / target | Template | Engine variants |
|---|---|---|
| `AWS::RDS::DBInstance` | RDS single-user (rotates master) | MySQL, PostgreSQL, Oracle, SQL Server, MariaDB |
| `AWS::RDS::DBInstance` | RDS multi-user (creates new rotating user) | MySQL, PostgreSQL, Oracle, SQL Server |
| `AWS::RDS::DBCluster` | Aurora cluster | Aurora MySQL, Aurora PostgreSQL |
| `AWS::Redshift::Cluster` | Redshift | Redshift |
| `AWS::DocDB::DBCluster` | DocumentDB | DocumentDB |
| `AWS::AmazonMQ::Broker` | Amazon MQ | ActiveMQ |
| `AWS::Neptune::DBCluster` | Neptune | Neptune |
| Type `Other` | No managed template — custom Lambda required | N/A |

Deploy via Serverless Application Repository (SAR) or CloudFormation. The
console's "Enable rotation" wizard deploys the template automatically.

## Custom Lambda skeleton (Python)

```python
import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

service_client = boto3.client('secretsmanager')

def lambda_handler(event, context):
    """Secrets Manager rotation Lambda handler.

    Args:
        event: dict with keys SecretId, ClientRequestToken, Step.
    """
    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    # Sanity: make sure the version is staged as AWSPENDING
    metadata = service_client.describe_secret(SecretId=arn)
    if not metadata['RotationEnabled']:
        logger.error(f"Secret {arn} is not enabled for rotation")
        raise ValueError(f"Secret {arn} is not enabled for rotation")
    versions = metadata['VersionIdsToStages']
    if token not in versions:
        logger.error(f"Attempted to access invalid token {token}")
        raise ValueError(f"Invalid stage token {token}")
    if 'AWSPENDING' not in versions[token]:
        logger.error(f"Token {token} not in AWSPENDING")
        raise ValueError(f"Invalid stage token {token}")

    if step == 'createSecret':
        create_secret(service_client, arn, token)
    elif step == 'setSecret':
        set_secret(service_client, arn, token)
    elif step == 'testSecret':
        test_secret(service_client, arn, token)
    elif step == 'finishSecret':
        finish_secret(service_client, arn, token)
    else:
        raise ValueError(f"Invalid step {step}")


def create_secret(service_client, arn, token):
    """Generate a new credential and store it as AWSPENDING."""
    # Check if the current AWSPENDING version already exists (reinvoke safety)
    try:
        service_client.get_secret_value(SecretId=arn, VersionId=token,
                                         VersionStage='AWSPENDING')
        logger.info(f"createSecret: AWSPENDING version {token} already exists")
        return
    except service_client.exceptions.ResourceNotFoundException:
        pass

    # Get the current secret value to understand the structure
    current = service_client.get_secret_value(SecretId=arn,
                                               VersionStage='AWSCURRENT')
    current_dict = json.loads(current['SecretString'])

    # Generate new credential — MODIFY THIS for the target service
    new_password = generate_password()

    # Copy the current dict and replace the password field
    new_dict = current_dict.copy()
    new_dict['password'] = new_password

    service_client.put_secret_value(
        SecretId=arn,
        ClientRequestToken=token,
        SecretString=json.dumps(new_dict),
        VersionStages=['AWSPENDING']
    )
    logger.info(f"createSecret: put AWSPENDING version {token}")


def set_secret(service_client, arn, token):
    """Apply the AWSPENDING credential to the target service.

    For RDS PostgreSQL: connect with AWSCURRENT, ALTER USER password.
    For an API: PUT /credential with the new value.
    """
    pending = service_client.get_secret_value(SecretId=arn, VersionId=token,
                                               VersionStage='AWSPENDING')
    pending_dict = json.loads(pending['SecretString'])

    # MODIFY THIS BLOCK to apply the credential to the target service.
    # Example for PostgreSQL:
    #   import psycopg2
    #   current = service_client.get_secret_value(SecretId=arn,
    #       VersionStage='AWSCURRENT')
    #   current_dict = json.loads(current['SecretString'])
    #   conn = psycopg2.connect(host=current_dict['host'],
    #       port=current_dict['port'], dbname=current_dict['dbname'],
    #       user=current_dict['username'], password=current_dict['password'],
    #       connect_timeout=10)
    #   cur = conn.cursor()
    #   cur.execute(f"ALTER USER {pending_dict['username']} "
    #               f"WITH PASSWORD %s", (pending_dict['password'],))
    #   conn.commit()
    #   conn.close()
    pass


def test_secret(service_client, arn, token):
    """Verify the AWSPENDING credential works against the target."""
    pending = service_client.get_secret_value(SecretId=arn, VersionId=token,
                                               VersionStage='AWSPENDING')
    pending_dict = json.loads(pending['SecretString'])

    # MODIFY THIS BLOCK to log in with the pending credential.
    # Example for PostgreSQL:
    #   conn = psycopg2.connect(host=pending_dict['host'],
    #       port=pending_dict['port'], dbname=pending_dict['dbname'],
    #       user=pending_dict['username'], password=pending_dict['password'],
    #       connect_timeout=10)
    #   conn.close()
    pass


def finish_secret(service_client, arn, token):
    """Promote AWSPENDING to AWSCURRENT."""
    # Find the current AWSCURRENT version (to move to AWSPREVIOUS)
    metadata = service_client.describe_secret(SecretId=arn)
    current_version = next(
        v for v, stages in metadata['VersionIdsToStages'].items()
        if 'AWSCURRENT' in stages
    )
    service_client.update_secret_version_stage(
        SecretId=arn,
        VersionStage='AWSCURRENT',
        MoveToVersionId=token,
        RemoveFromVersionId=current_version
    )
    logger.info(f"finishSecret: promoted {token} to AWSCURRENT")


def generate_password(length=32):
    """Generate a password safe for the target service.

    AVOID characters that break the target's parser:
    - MySQL: avoid `@`, `$`, `\` (interpreted by some clients)
    - PostgreSQL: avoid `'` (quote)
    - URLs: avoid `/`, `?`, `#`, `&`
    """
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + '!%^*()-_=+'
    # Edit per-target as needed
    return ''.join(secrets.choice(alphabet) for _ in range(length))
```

Set the Lambda timeout to at least 30 seconds. 60 seconds for Aurora
clusters with many instances. Configure via:

```bash
aws lambda update-function-configuration \
  --function-name <rotation-lambda> \
  --timeout 30
```

## IAM execution role — required permissions

### Same-account, default KMS key (`aws/secretsmanager`)

Attach the AWS-managed `SecretsManagerRotation` policy:

```bash
aws iam attach-role-policy \
  --role-name <role> \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerRotation
```

### Same-account, customer-managed CMK (least-privilege custom policy)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:DescribeSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:UpdateSecretVersionStage"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/<name>-??????"
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:us-east-1:111111111111:key/<cmk-id>"
    }
  ]
}
```

The `-??????` suffix is required because Secrets Manager auto-appends a
random 6-character string to the secret name in the ARN.

### Database-target additions

| Engine | Required permission | Resource |
|---|---|---|
| RDS (MySQL/PostgreSQL/Oracle/SQLServer/MariaDB) | `rds-db:connect` | `arn:aws:rds-db:<region>:<account>:dbuser:<db-resource-id>/<db-user>` |
| Aurora (MySQL/PostgreSQL) | `rds-db:connect` | `arn:aws:rds-db:<region>:<account>:dbuser:<cluster-resource-id>/<db-user>` |
| Redshift | `redshift:GetClusterCredentials` | `arn:aws:redshift:<region>:<account>:cluster:<cluster-name>` |
| DocumentDB | DocumentDB does not use IAM auth; the Lambda connects with master credentials from the secret | N/A |
| AmazonMQ | Standard STomp/AMQP connection; no IAM | N/A |

Find the `db-resource-id` (NOT the cluster identifier) via:

```bash
aws rds describe-db-instances --db-instance-identifier <id> \
  --query 'DBInstances[0].DbiResourceId' --output text
aws rds describe-db-clusters --db-cluster-identifier <id> \
  --query 'DBClusters[0].DbClusterResourceId' --output text
```

### VPC-attached Lambda additions

For database targets in a VPC, the Lambda needs network-interface
permissions:

```bash
aws iam attach-role-policy \
  --role-name <role> \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
```

This grants `ec2:CreateNetworkInterface`,
`ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface`.

## Lambda resource-based policy

Secrets Manager invokes the Lambda as the `secretsmanager.amazonaws.com`
service principal. Add the resource-based policy:

### Same-account

```bash
aws lambda add-permission \
  --function-name <rotation-lambda> \
  --statement-id SecretsManagerAccess \
  --principal secretsmanager.amazonaws.com \
  --action lambda:InvokeFunction \
  --source-arn arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/<name>-??????
```

The `--source-arn` condition restricts the principal to invoking the
Lambda only for the specific secret. Without it, Secrets Manager in the
same account can invoke the Lambda for any secret.

### Cross-account

For a rotation Lambda in account B (Lambda account) and a secret in
account A (Secret account):

**In account B (Lambda account):**

```bash
aws lambda add-permission \
  --function-name <rotation-lambda> \
  --statement-id SecretsManagerCrossAccount \
  --principal secretsmanager.amazonaws.com \
  --action lambda:InvokeFunction \
  --source-arn arn:aws:secretsmanager:us-east-1:AAAAAAAAAAAA:secret:prod/<name>-?????? \
  --source-account AAAAAAAAAAAA
```

**In account A (Secret account), attach a resource-based policy on the
secret:**

```bash
aws secretsmanager put-resource-policy \
  --secret-id prod/<name> \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::BBBBBBBBBBBB:role/<lambda-role>"},
        "Action": [
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage"
        ],
        "Resource": "*"
      }
    ]
  }'
```

The Lambda role in account B must ALSO have the same actions on the
cross-account secret ARN in its identity-based policy. Both sides of the
grant are required.

## Single-user vs multi-user rotation (RDS)

| Mode | Behavior | When to use |
|---|---|---|
| Single-user | Rotates the master credential. Connects as master, runs `ALTER USER master PASSWORD`. The username stays the same; only the password changes. | Default. Use when applications cache the username and only the password is read from the secret. |
| Multi-user | Creates a new rotating user (e.g., `app_rw_01`, `app_rw_02`); the secret alternates between them. The previous user is DELETED after the new one is verified. | Use when the master credential must remain stable, or when applications tolerate a username change. Avoids the "single writer" limitation. |

Deploy multi-user mode via the multi-user template in the SAR (Serverless
Application Repository). The secret must contain a `masterSecret` field
pointing to a separate secret holding the master credentials the Lambda
uses to create/rotate users.

## Schedule configuration

### AutomaticallyAfterDays (simple interval)

```bash
aws secretsmanager rotate-secret \
  --secret-id prod/<name> \
  --rotation-lambda-arn arn:aws:lambda:<region>:<account>:function:<lambda> \
  --rotation-rules AutomaticallyAfterDays=30
```

Range: 1-365. Secrets Manager rotates within a 24-hour window starting at
midnight UTC on the scheduled day, with jitter.

### ScheduleExpression (cron / rate)

```bash
aws secretsmanager rotate-secret \
  --secret-id prod/<name> \
  --rotation-lambda-arn arn:aws:lambda:<region>:<account>:function:<lambda> \
  --rotation-rules ScheduleExpression="cron(0 9 ? * MON *)"
```

When `ScheduleExpression` is present, it overrides
`AutomaticallyAfterDays`. Use cron for time-of-day or day-of-week
requirements. The `?` in day-of-month is required when day-of-week is
specified. All times are UTC.

### Rotate immediately on enable

Calling `rotate-secret` with `--rotation-lambda-arn` triggers the first
rotation immediately. To enable rotation WITHOUT an immediate trigger,
use `update-secret-version-stage` is NOT correct — use:

```bash
aws secretsmanager rotate-secret \
  --secret-id prod/<name> \
  --rotation-lambda-arn arn:aws:lambda:<region>:<account>:function:<lambda> \
  --rotation-rules AutomaticallyAfterDays=30 \
  --rotate-immediately false
```

The `--rotate-immediately false` flag (added 2023) defers the first
rotation to the next scheduled interval.

## Common failure signatures in CloudWatch Logs

| CloudWatch Logs pattern | Root cause | Fix |
|---|---|---|
| `Task timed out after 3.00 seconds` | Lambda timeout too short | `update-function-configuration --timeout 30` |
| `AccessDeniedException` on `secretsmanager:GetSecretValue` | Lambda role missing permissions or secret resource policy denies role | Attach policy; check secret resource policy |
| `DecryptionFailureException` | KMS key policy denies Lambda role | Add `kms:Decrypt` grant on key |
| `ResourceNotFoundException` on target RDS | DB instance deleted or wrong host in secret | Update secret `host`/`port`; verify DB exists |
| `OperationalError: FATAL: password authentication failed for user` | AWSCURRENT credential was manually changed out-of-band | Update secret value to match; then trigger rotation |
| `ThrottledReason: ConcurrentInvocationRateExceeded` | Reserved concurrency = 0 or account concurrency exhausted | Set reserved concurrency >= 1 |
| `InvalidParameterValue: Invalid password` | Generated password has forbidden chars for the target | Edit the password generator in the Lambda |
| No log entries at all (Lambda never invoked) | Resource-based policy missing principal; OR replica secret | Verify Lambda policy; check `PrimaryRegion` |
