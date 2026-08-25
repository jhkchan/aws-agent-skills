# Diagnostic Commands — CloudTrail Alert Automation

Load-on-demand query and diagnostic command listings for the CloudTrail Alert
Automator skill.

## Step 10: CloudTrail Lake for historical queries

```bash
# Create event data store
aws cloudtrail create-event-data-store \
  --name cloudtrail-alert-eds \
  --advanced-event-selectors '[{"Name":"MgmtEvents","FieldSelectors":[{"Field":"eventCategory","Equals":["Management"]}]}]'

# Query actor activity in last 24h
QUERY_ID=$(aws cloudtrail start-query \
  --query-statement "SELECT eventName, eventTime, sourceIPAddress FROM <EDS_ID> WHERE userIdentity.arn = ''arn:aws:iam::111111111111:user/suspicious'' AND eventTime > timestamp(''2026-08-10T00:00:00Z'')" \
  --query 'QueryId' --output text)
aws cloudtrail get-query-results --query-id $QUERY_ID
```
