# End-to-End Example: CloudTrail Lake Deployment

A walkthrough showing how to use the `cloudtrail-lake-query-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a CloudTrail Lake management events EDS with
90-day retention, data protection (PII masking), CloudWatch alerting,
and forensic query capability. The setup needs:

- EDS: mgmt-events-eds
- Event type: Management events
- Retention: 90 days
- Data protection: mask EmailAddress and PhoneNumber
- CloudWatch alarm: query failures to SNS
- Tags: Environment=production, Domain=security

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-cloudtrail-lake-query
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a CloudTrail Lake EDS for management events. 90-day
      retention. Mask email and phone. CloudWatch alarm for query
      failures."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create cloudtrail lake eds"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
CLOUDTRAIL_LAKE: mgmt-events-eds (arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/abc123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Event data store: mgmt-events-eds (arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/abc123)
  [✓] Event type: Management events
  [✓] Retention: 90 days
  [✓] Data protection: EmailAddress, PhoneNumber masked
  [✓] Query API: cloudtrail-data (StartQuery + GetQueryResults)
  [✓] CloudWatch alerting: cloudtrail-lake-query-failures
  [✓] Billing: $0.75/GB ingested + $0.005/GB scanned
  [✓] Tags: Environment=production, Domain=security
VERIFICATION_COMMANDS:
  aws cloudtrail list-event-data-stores
  aws cloudtrail-data start-query --query-statement "SELECT count(*) FROM arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/abc123 WHERE eventTime > '2026-08-10T00:00:00Z'"
  aws cloudtrail get-data-protection-policy --event-data-store-id abc123
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the EDS
EDS_ID=$(aws cloudtrail create-event-data-store \
  --name "mgmt-events-eds" \
  --include-management-events \
  --retention-period 90 \
  --query 'EventDataStoreArn' --output text)

# Step 2: Apply data protection policy
aws cloudtrail put-data-protection-policy \
  --event-data-store "$EDS_ID" \
  --policy-document '{
    "Configuration": {"Mode": "Mask", "MaskingStyle": "REPLACE_WITH_MASK"},
    "Identifiers": [
      "arn:aws:dataprotection:us-east-1:aws:data-identifier/EmailAddress",
      "arn:aws:dataprotection:us-east-1:aws:data-identifier/PhoneNumber"
    ]
  }'

# Step 3: Create CloudWatch alarm for query failures
aws cloudwatch put-metric-alarm \
  --alarm-name "cloudtrail-lake-query-failures" \
  --namespace AWS/CloudTrailLake \
  --metric-name QueryFailureCount \
  --statistic Sum --period 300 --evaluation-periods 1 \
  --threshold 5 --comparison-operator GreaterThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:ct-lake-alerts"

# Step 4: Test forensic query
QUERY_ID=$(aws cloudtrail-data start-query \
  --query-statement "SELECT eventName, eventTime, userIdentity.arn FROM $EDS_ID WHERE eventTime > '2026-08-10T00:00:00Z' AND eventTime < '2026-08-11T00:00:00Z' LIMIT 10" \
  --query 'QueryId' --output text)

aws cloudtrail-data get-query-results --query-id "$QUERY_ID"
```

---

## Step 4 — Post-deployment verification

```bash
# Verify EDS
aws cloudtrail list-event-data-stores

# Verify data protection
aws cloudtrail get-data-protection-policy \
  --event-data-store-id "$(echo $EDS_ID | rev | cut -d/ -f1 | rev)"

# Test query (who deleted resources in last 24h)
aws cloudtrail-data start-query \
  --query-statement "SELECT userIdentity.arn, eventName, eventTime FROM $EDS_ID WHERE eventTime > '2026-08-10T00:00:00Z' AND eventName LIKE 'Delete%' ORDER BY eventTime DESC LIMIT 10"
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Event type | Not decided (immutable after creation) | Explicit decision before creation | EDS type CANNOT be changed later |
| Query API | Uses cloudtrail API | Uses cloudtrail-data API (separate) | Different APIs for config vs query |
| Time range in queries | No time filter (scans all) | Always specify time range | Reduces cost; queries scan raw JSON |
| Data protection | Not configured | PII masking before query results | Masks PII at storage level, permanent |
| Billing model | Unknown | Per-GB ingested + per-GB scanned | Both costs must be budgeted |
| Selectors for data events | All data events (expensive) | Filtered by resource and event name | Reduces ingestion cost dramatically |

---

## Related artifacts

- **Skill definition:** `skills/cloudtrail-lake-query-deployer/SKILL.md`
- **Querying guide:** `skills/cloudtrail-lake-query-deployer/references/querying-and-forensics.md`
- **EDS and multi-account guide:** `skills/cloudtrail-lake-query-deployer/references/eds-and-multi-account.md`
- **Slash command:** `commands/aws/deploy-cloudtrail-lake-query.md`
- **Eval suite:** `skills/cloudtrail-lake-query-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cloudtrail-lake-query-deployer/eval/test-cases.yaml`
