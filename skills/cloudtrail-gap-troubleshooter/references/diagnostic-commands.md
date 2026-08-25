# CloudTrail Gap Diagnostic Commands — Reference

Supplementary reference for the CloudTrail Gap Troubleshooter skill.
The canonical command script per failure category, with sample outputs
and interpretation notes.

## Universal first commands (run for any CloudTrail gap)

```bash
# 1. List all trails and their key config flags.
aws cloudtrail describe-trails \
  --query 'trailList[*].{name:Name,multi:IsMultiRegionTrail,org:IsOrganizationTrail,global:IncludeGlobalServiceEvents,s3:S3BucketName,prefix:S3KeyPrefix,kms:KmsKeyId,validation:LogFileValidationEnabled,logging:IsLogging,home:HomeRegion}'

# 2. Per-trail status (run for each trail).
aws cloudtrail get-trail-status --name <trail> \
  --query '{isLogging:IsLogging,latestDelivery:LatestDeliveryTime,latestDigest:LatestDigestDeliveryTime,latestCWL:LatestCloudWatchLogsDeliveryTime,started:StartLoggingTime,stopped:StopLoggingTime}'

# 3. Recent events to confirm whether ANY events are flowing.
aws cloudtrail lookup-events --max-results 5 \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --query 'Events[*].{time:EventTime,name:EventName,source:CloudTrailEvent}'

# 4. Event selectors (for MISSING_DATA_EVENTS).
aws cloudtrail get-event-selectors --trail-name <trail>
```

The `IsLogging` flag from `get-trail-status` is the canonical health
signal. `describe-trails.IsLogging` is a cached snapshot and can lag
by minutes — prefer `get-trail-status`.

## Per-category command scripts

### Category A: MISSING_DATA_EVENTS

```bash
# Read event selectors (basic mode):
aws cloudtrail get-event-selectors --trail-name <trail>

# Read advanced event selectors (advanced mode — mutually exclusive):
aws cloudtrail get-event-selectors --trail-name <trail>
# (returns AdvancedEventSelectors if the trail uses advanced mode)

# Confirm management events are flowing:
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateBucket \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 5

# Confirm the missing data event is NOT flowing:
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 5

# Verify directly in S3 delivery (events may be in S3 but not in the
# 90-day lookup-events window):
aws s3api list-objects-v2 \
  --bucket <bucket> \
  --prefix "AWSLogs/<account>/CloudTrail/<region>/$(date -u +%Y/%m/%d)/" \
  --query 'Contents[*].Key' --output text | tr '\t' '\n' | tail -5

# Add S3 data events (basic event selector):
aws cloudtrail put-event-selectors --trail-name <trail> \
  --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[{"Type":"AWS::S3::Object","Values":["arn:aws:s3:::audit-bucket/"]}]}]'

# Add S3 data events (advanced event selector, for per-bucket scoping):
aws cloudtrail put-event-selectors --trail-name <trail> \
  --advanced-event-selectors '[
    {"Name":"Management events selector","FieldSelectors":[
      {"Field":"eventCategory","Equals":["Management"]}
    ]},
    {"Name":"S3 data events for audit-bucket","FieldSelectors":[
      {"Field":"eventCategory","Equals":["Data"]},
      {"Field":"resources.type","Equals":["AWS::S3::Object"]},
      {"Field":"resources.ARN","StartsWith":["arn:aws:s3:::audit-bucket/"]}
    ]}
  ]'
```

**Interpretation:**

- `DataResources` empty → no data events configured.
- `DataResources` with `Type: AWS::S3::Object` and `Values:
  ["arn:aws:s3"]` → all S3 data events (high volume / cost).
- `DataResources` with `Values: ["arn:aws:s3:::audit-bucket/"]` →
  only the audit-bucket prefix.
- `AdvancedEventSelectors` with `Field: resources.type` → modern
  per-resource-type scoping.

### Category B: TRAIL_NOT_LOGGING

```bash
# Trail status (the canonical signal):
aws cloudtrail get-trail-status --name <trail>

# Trail config:
aws cloudtrail describe-trails --trail-name-list <trail>

# Shadow trails (deleted trails retained for 30 days):
aws cloudtrail describe-trails --show-shadow-trails \
  --query 'trailList[*].{name:Name,shadow:IsShadowTrail,logging:IsLogging,region:HomeRegion}'

# Restart logging:
aws cloudtrail start-logging --name <trail>

# Verify it restarted:
aws cloudtrail get-trail-status --name <trail> --query 'IsLogging'
```

**Interpretation:**

- `IsLogging: false` + `StopLoggingTime` populated → trail was
  explicitly stopped.
- `IsLogging: false` + no `StartLoggingTime` → trail was created but
  logging was never started (IaC gap).
- Trail missing from `describe-trails` → trail was deleted; use
  `--show-shadow-trails` to find the config.

### Category C: DELIVERY_DELAYED

```bash
# Latest delivery times:
aws cloudtrail get-trail-status --name <trail> \
  --query '{isLogging:IsLogging,latestDelivery:LatestDeliveryTime,latestDigest:LatestDigestDeliveryTime,latestCWL:LatestCloudWatchLogsDeliveryTime}'

# Bucket region:
aws s3api get-bucket-location --bucket <bucket>

# Trail region:
aws cloudtrail describe-trails --trail-name-list <trail> \
  --query 'trailList[0].HomeRegion'

# AWS Health (CLI v2):
aws health describe-events --filter eventStatusCodes=open,upcoming \
  --region us-east-1 \
  --query 'events[?service==`CLOUDTRAIL`]'

# Most recent log file in S3:
aws s3 ls s3://<bucket>/AWSLogs/<account>/CloudTrail/<region>/ \
  --recursive | sort | tail -3
```

**Interpretation:**

- `LatestDeliveryTime` lagging `now` by > 15 min for management events
  → DELIVERY_DELAYED.
- Bucket in a different region than trail → expected latency.
- AWS Health open event for CloudTrail → service issue (no operator
  fix).
- Org trail: member account events lag management by 5-15 min
  (expected).

### Category D: INSIGHTS_DISABLED

```bash
# Read Insights selectors:
aws cloudtrail get-insight-selectors --trail-name <trail>
# Expected: {"InsightSelectors":[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]}

# Read per-source Insights selectors (newer API, 2024+):
aws cloudtrail list-insights-selectors --trail-name <trail>

# Verify the trail is actively logging (Insights requires this):
aws cloudtrail get-trail-status --name <trail> --query 'IsLogging'

# Enable Insights (legacy API — toggles globally):
aws cloudtrail put-insight-selectors --trail-name <trail> \
  --insight-selectors '[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]'

# Check for Insights findings in S3:
aws s3 ls s3://<bucket>/CloudTrail-Insight/ --recursive | tail -5

# Query Insights findings via Lake (if integrated):
aws cloudtrail query --query-statement "SELECT eventID, eventName, eventTime, insightContext FROM <eds-id> WHERE eventType='AwsCloudTrailInsight'"
```

**Interpretation:**

- `InsightSelectors` empty → Insights is OFF.
- `InsightSelectors` populated but trail `IsLogging: false` → Insights
  has nothing to analyze; fix B first.
- `InsightSelectors` populated + trail logging + no findings in first
  7 days → baseline period not elapsed.

### Category E: ORG_TRAIL_GAP

```bash
# Management account:
aws cloudtrail describe-trails \
  --query 'trailList[?IsOrganizationTrail].{name:Name,isLogging:IsLogging,s3:S3BucketName,home:HomeRegion}'

aws cloudtrail get-trail-status --name <org-trail>

# Delegated admin check:
aws organizations list-delegated-administrators \
  --service-principal cloudtrail.amazonaws.com \
  --query 'DelegatedAdministrators[*].{id:Id,name:AccountName,email:EmailAddress,status:Status}'

# Verify the member account is in the org:
aws organizations list-accounts \
  --query 'Accounts[?Id==`<member-acct-id>`].{id:Id,status:Status,name:Name}'

# Member account (use member-account profile):
aws cloudtrail describe-trails --show-shadow-trails \
  --query 'trailList[*].{name:Name,shadow:IsShadowTrail,logging:IsLogging,isOrg:IsOrganizationTrail}'

# Restart logging in the member (member credentials):
aws cloudtrail start-logging --name <org-trail>

# Check SCPs applied to the member or its OU:
aws organizations list-policies-for-target \
  --target-id <member-or-ou-id> \
  --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[*].{id:Id,name:Name,type:Type}'
```

**Interpretation:**

- Org trail `IsLogging: false` in management account → all members
  affected; restart from management.
- Member shadow trail `IsLogging: false` → only that member affected;
  restart from member.
- Member not in `organizations list-accounts` or `Status: SUSPENDED`
  → member is no longer being logged by design.
- Two org trails (one in management, one in delegated admin) →
  conflict; delete one.

### Category F: MULTI_REGION_GAP

```bash
aws cloudtrail describe-trails --trail-name-list <trail> \
  --query 'trailList[0].{multi:IsMultiRegionTrail,global:IncludeGlobalServiceEvents,home:HomeRegion}'

# Search a specific region directly (event history is per-region):
aws cloudtrail lookup-events --region us-west-2 \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 5 \
  --query 'Events[*].{time:EventTime,name:EventName}'

# Convert to multi-region:
aws cloudtrail update-trail --name <trail> \
  --is-multi-region-trail \
  --include-global-service-events
```

**Interpretation:**

- `IsMultiRegionTrail: false` + events missing from a non-home region
  → MULTI_REGION_GAP.
- `IncludeGlobalServiceEvents: false` + IAM/STS events missing →
  enable global service events.
- `IsMultiRegionTrail: true` + events from one region still missing →
  check AWS Health for that region.

### Category G: BUCKET_POLICY_BLOCKING

```bash
# Read the bucket policy:
aws s3api get-bucket-policy --bucket <bucket> --query Policy --output text | jq .

# Verify CloudTrail Allow statements:
aws s3api get-bucket-policy --bucket <bucket> --query Policy --output text | \
  jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com" or (.Principal.Service // "" | tostring | contains("cloudtrail")))'

# Look for explicit Denies that might override:
aws s3api get-bucket-policy --bucket <bucket> --query Policy --output text | \
  jq '.Statement[] | select(.Effect=="Deny")'

# Verify KMS key policy (if KMSKeyId is set):
aws kms get-key-policy --key-id <key-id> --policy-name default --query Policy --output text | \
  jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com")'

# Most recent log file delivery:
aws s3 ls s3://<bucket>/AWSLogs/<account>/CloudTrail/ --recursive | sort | tail -3

# Cross-account verification (bucket in different account):
aws s3api get-bucket-policy --bucket <bucket> --query Policy --output text | \
  jq '.Statement[] | select(.Resource | tostring | contains("<trail-account-id>"))'
```

**Interpretation:**

- No Allow statement for `cloudtrail.amazonaws.com` → bucket policy
  missing entirely.
- Allow statement without `Condition: StringEquals:
  s3:x-amz-acl=bucket-owner-full-control` → common omission; may cause
  silent failures depending on bucket ownership controls.
- Allow for one account ID but trail is in another → cross-account
  mismatch.
- KMS key policy missing `cloudtrail.amazonaws.com` → encryption
  fails silently; no log files delivered.
- Explicit Deny overriding the Allow → typically added by a restrictive
  SCP or bucket policy update.

## Combining signals — the diagnostic trinity

```bash
# 1. CONFIGURATION (what the trail is supposed to do):
aws cloudtrail describe-trails --trail-name-list <trail>

# 2. STATUS (what the trail is actually doing):
aws cloudtrail get-trail-status --name <trail>

# 3. EVENT SELECTORS (which events are in scope):
aws cloudtrail get-event-selectors --trail-name <trail>
```

These three commands answer:

- **describe-trails:** is it multi-region? Org trail? Where does it
  write? Is KMS configured?
- **get-trail-status:** is it actively logging? When was the last
  successful delivery?
- **get-event-selectors:** are data events configured? Are any event
  sources excluded?

Always start with all three. The category letter (A-G) follows from
which signal reveals the gap.

## Live-account CloudTrail context commands

When you need account-level context:

```bash
# List all event data stores (CloudTrail Lake):
aws cloudtrail list-event-data-stores \
  --query 'EventDataStores[*].{id:EventDataStoreArn,name:Name,status:Status,retention:RetentionPeriod,insights:AdvancedEventSelectors}'

# Read a specific event data store:
aws cloudtrail get-event-data-store --event-data-store <eds-id>

# Query CloudTrail Lake:
aws cloudtrail query --query-statement "SELECT eventName, eventTime, userIdentity.arn, awsRegion FROM <eds-id> WHERE eventName='PutBucketPolicy' AND eventTime > '2026-08-09T00:00:00Z'"

# Check Organizations context (for org trail issues):
aws organizations describe-organization \
  --query 'Organization.{id:Id,mgmt:MasterAccountId,featureSet:FeatureSet}'

# List CloudTrail-related IAM actions performed recently (cloud forensics):
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=cloudtrail.amazonaws.com \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ) \
  --max-results 20 \
  --query 'Events[*].{time:EventTime,name:EventName,user:Username}'

# CloudTrail metrics (delivery volume):
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudTrail \
  --metric-name NumberOfNotificationsDelivered \
  --dimensions Name=TrailName,Value=<trail> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum
```

## Output verification commands

After applying a fix:

```bash
# For start-logging fixes: verify status flipped.
aws cloudtrail get-trail-status --name <trail> --query 'IsLogging'

# For event-selector fixes: make a test API call, then check lookup-events.
aws s3 cp s3://audit-bucket/cloudtrail-test . && \
  sleep 600 && \
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
    --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ) \
    --max-results 5

# For bucket-policy fixes: wait 5-15 min, then list the latest log file.
aws s3 ls s3://<bucket>/AWSLogs/<account>/CloudTrail/ --recursive | sort | tail -3

# For multi-region fixes: make a test call in a previously-missing region.
aws s3 ls --region us-west-2 && \
  sleep 600 && \
  aws cloudtrail lookup-events --region us-east-1 \
    --lookup-attributes AttributeKey=EventName,AttributeValue=ListBuckets \
    --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ) \
    --max-results 5

# For org trail fixes: check the member account's events in the org
# bucket.
aws s3 ls s3://<org-bucket>/AWSLogs/<member-account-id>/CloudTrail/ \
  --recursive | sort | tail -3

# For Insights fixes: wait 7 days, then check the CloudTrail-Insight prefix.
aws s3 ls s3://<bucket>/CloudTrail-Insight/ --recursive | tail -5

## Step 2 — MISSING_DATA_EVENTS diagnostic commands (moved from SKILL.md)

```bash
# Read the trail's event selectors:
aws cloudtrail get-event-selectors --trail-name <trail>

# Search S3 log delivery directly for the expected event:
aws s3 cp s3://<bucket>/<key> - | gzip -d | jq '.Records[] | select(.eventName=="GetObject")'

# Or use CloudTrail Lake to query across all regions/accounts:
aws cloudtrail query --query-statement "SELECT eventName, eventTime, userIdentity.arn FROM <eds-id> WHERE eventName='GetObject' AND eventTime > '2026-08-09T00:00:00Z'"
```

## Step 3 — TRAIL_NOT_LOGGING diagnostic commands (moved from SKILL.md)

```bash
# Trail status (canonical health signal):
aws cloudtrail get-trail-status --name <trail> \
  --query '{isLogging:IsLogging,latestDelivery:LatestDeliveryTime,latestDigest:LatestDigestDeliveryTime,started:StartLoggingTime,stopped:StopLoggingTime}'

# If trail is missing, look for shadow (deleted) trails:
aws cloudtrail describe-trails --show-shadow-trails \
  --query 'trailList[*].{name:Name,shadow:IsShadowTrail,logging:IsLogging,region:HomeRegion}'

# Verify KMS key policy (if KMSKeyId is set):
aws kms get-key-policy --key-id <key-id> --policy-name default \
  --query Policy --output text | jq '.Statement[] | select(.Principal.Service=="cloudtrail.amazonaws.com")'

# Restart logging if stopped:
aws cloudtrail start-logging --name <trail>
```

## Step 6 — ORG_TRAIL_GAP diagnostic commands (moved from SKILL.md)

```bash
# Management account:
aws cloudtrail describe-trails --query 'trailList[?IsOrganizationTrail].{name:Name,isLogging:IsLogging,s3:S3BucketName,homeRegion:HomeRegion}'
aws cloudtrail get-trail-status --name <org-trail>

# Delegated admin check:
aws organizations list-delegated-administrators \
  --service-principal cloudtrail.amazonaws.com \
  --query 'DelegatedAdministrators[*].{id:Id,name:AccountName,email:EmailAddress}'

# Member account (use member-account profile):
aws cloudtrail describe-trails --show-shadow-trails \
  --query 'trailList[*].{name:Name,shadow:IsShadowTrail,logging:IsLogging,isOrg:IsOrganizationTrail}'

# Verify member is in the org and ACTIVE:
aws organizations list-accounts --query 'Accounts[?Id==`<member-acct-id>`].{id:Id,status:Status,name:Name}'

# Check SCPs applied to the member account's OU:
aws organizations list-policies-for-target --target-id <member-or-ou-id> \
  --filter SERVICE_CONTROL_POLICY
```
