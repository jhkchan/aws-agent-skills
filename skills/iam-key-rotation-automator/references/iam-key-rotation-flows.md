# IAM Key Rotation Flows Reference

Supplementary reference for the IAM Key Rotation Automator skill. Use
when designing a rotation flow, selecting the right rotation pattern,
or debugging a rotation failure.

## Rotation flow patterns

### Pattern 1: Standard rotation (single account, overlap window)

The most common pattern. Used when an IAM user's key is aged >= 90 days
and the application can tolerate a brief overlap period.

**Flow:**

```
Day 0:   Create new key (slot 2)
          Store secret in Secrets Manager
          Verify new key via STS
Day 0-1: Application picks up new key from Secrets Manager
Day 1-7: Both keys active (overlap window)
          Monitor old key usage via access advisor
Day 7:   Deactivate old key (if not used in 24h)
Day 7-10: Old key Inactive, monitor app health
Day 10:  Delete old key
```

**CLI commands:**

```bash
# Create new key
aws iam create-access-key --user-name deployment-user

# Verify new key
aws sts get-caller-identity \
  --aws-access-key-id AKIANEW \
  --aws-secret-access-key <new-secret>

# Deactivate old key
aws iam update-access-key --user-name deployment-user \
  --access-key-id AKIAOLD --status Inactive

# Delete old key
aws iam delete-access-key --user-name deployment-user \
  --access-key-id AKIAOLD
```

### Pattern 2: Expedited rotation (security incident)

Used when a key is suspected compromised. No overlap window — the old
key is deactivated immediately.

**Flow:**

```
Hour 0:  Create new key
          Store secret, update app config
Hour 0:  Deactivate old key IMMEDIATELY
Hour 0:  Verify new key works
Hour 1:  If new key fails, reactivate old key (rollback)
Hour 24: Delete old key after confirming new key stability
```

**Risk:** the application may experience a brief outage between old
key deactivation and new key deployment. Acceptable for compromised
keys; NOT recommended for routine rotation.

### Pattern 3: Zero-downtime rotation (critical production)

Used for critical production applications where even a brief
credential gap causes an outage. Extended overlap window with
monitoring.

**Flow:**

```
Day 0:    Create new key, store in Secrets Manager
Day 0:    Enable dual-key reading in application (if supported)
Day 0-14: Both keys active (extended overlap)
          Daily monitoring of old key usage
Day 14:   Deactivate old key (if not used in 48h)
Day 14-17: Old key Inactive, monitor app health
Day 17:   Delete old key
```

### Pattern 4: Break-glass manual rotation

Used for exception-listed accounts. No automation — full manual flow
with security team approval.

**Flow:**

```
1. Security team reviews the exception
2. If rotation approved:
   a. Create new key
   b. Update break-glass procedure documentation
   c. Distribute new key via secure channel (KMS-encrypted SSM)
   d. Deactivate old key
   e. Verify emergency access works
   f. Delete old key after 72h
3. Update exception list review_date
```

## Key slot management

IAM allows exactly 2 access keys per user. The slot state determines
the rotation approach:

| Slot 1 | Slot 2 | Rotation approach |
|---|---|---|
| Active (old) | Empty | Standard: create in slot 2, overlap, deactivate slot 1, delete |
| Active (old) | Active (newer) | Check if slot 2 is the newer key — if so, just delete slot 1 |
| Active (old) | Inactive | Delete inactive slot 2, then create new key in slot 2 |
| Empty | Active | Unusual — likely already rotated. Verify slot 2 key age. |

**When both slots are Active and both are in use:**
- This is a manual decision point. Do NOT auto-deactivate either key.
- Analyze `get-access-key-last-used` for both keys.
- The newer key is typically the one to keep; the older one to phase out.
- Notify the key owner before making any changes.

## Access advisor interpretation

```bash
# Per-key last-used
aws iam get-access-key-last-used --access-key-id AKIAXYZ123

# Per-service last-accessed for the user
aws iam generate-service-last-accessed-details --user-name deployment-user
aws iam get-service-last-accessed-details --job-id <id>
```

| Metric | Source | Granularity | Use case |
|---|---|---|---|
| Key last-used date | `get-access-key-last-used` | Per key | Pre-deactivation check |
| Service last-accessed | `generate-service-last-accessed-details` | Per service | Understand which APIs the key uses |
| Credential report | `get-credential-report` | Per user | Fleet-wide audit |

## Secrets Manager integration pattern

The recommended pattern for storing and rotating access keys via
Secrets Manager:

```python
import boto3, json
sm = boto3.client('secretsmanager')
iam = boto3.client('iam')

def rotate_key_in_secrets(user_name, secret_id):
    # Create new key
    new_key = iam.create_access_key(UserName=user_name)['AccessKey']

    # Update secret with new key
    sm.put_secret_value(
        SecretId=secret_id,
        SecretString=json.dumps({
            'access_key_id': new_key['AccessKeyId'],
            'secret_access_key': new_key['SecretAccessKey']
        })
    )

    # Return old key ID for later deactivation
    return new_key['AccessKeyId']
```

**Application-side reading (with auto-refresh):**

```python
import boto3, json, threading, time

class KeyProvider:
    def __init__(self, secret_id):
        self.sm = boto3.client('secretsmanager')
        self.secret_id = secret_id
        self._refresh()

    def _refresh(self):
        resp = self.sm.get_secret_value(SecretId=self.secret_id)
        creds = json.loads(resp['SecretString'])
        self._akid = creds['access_key_id']
        self._secret = creds['secret_access_key']

    def get_credentials(self):
        return self._akid, self._secret
```

## EventBridge Scheduler vs scheduled rules

For new deployments, prefer EventBridge Scheduler over classic
scheduled rules:

| Feature | Classic rule | EventBridge Scheduler |
|---|---|---|
| Per-target retry | No | Yes |
| Flexible cron | Limited | Full cron + rate |
| DLQ | Yes (target-level) | Yes (target-level) |
| Time zone | UTC only | Configurable |

```bash
# EventBridge Scheduler (newer)
aws scheduler create-schedule \
  --name iam-key-rotation-daily \
  --schedule-expression "rate(1 day)" \
  --flexible-time-window '{"Mode":"FLEXIBLE","MaximumWindowInMinutes":15}' \
  --target '{"RoleArn":"arn:aws:iam::111111111111:role/scheduler-role","Arn":"arn:aws:lambda:us-east-1:111111111111:function:iam-key-rotation"}'
```

## Common rotation failure signatures

| Failure | Root cause | Fix |
|---|---|---|
| Cannot create key — both slots full | User already has 2 active keys | Deactivate or delete one key first |
| New key verification fails | Secret not stored correctly | Check Secrets Manager value; re-store |
| App outage after deactivation | App reads key once at startup | Restart app or implement hot-reload |
| Old key still used after new key deployed | App caches credentials | Extend overlap; implement Secrets Manager auto-refresh |
| Cross-account sync fails | Target role trust policy missing | Add rotation role ARN to target role trust policy |
| Rotation Lambda times out | Too many users in one invocation | Paginate or split across multiple invocations |
