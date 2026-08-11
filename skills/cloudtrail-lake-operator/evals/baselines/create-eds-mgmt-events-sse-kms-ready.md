# Baseline (no-skill) response: create-eds-mgmt-events-sse-kms-ready

This file captures what a generic assistant produces WITHOUT the
cloudtrail-lake-operator skill loaded.

---

To create a CloudTrail Lake Event Data Store for your organization's
management events, use:

```bash
aws cloudtrail create-event-data-store \
  --name org-governance-edS \
  --kms-key-id arn:aws:kms:us-east-1:111111111111:key/edS-cmk \
  --retention-period 365 \
  --is-organization-service \
  --advanced-event-selectors '[{"Name":"mgmt","FieldSelectors":[{"Field":"eventCategory","Equals":["Management"]}]}]'
```

After creation, your organization's management events will start
flowing into the EDS within a few minutes. You can then run PartiQL
queries against the EDS using `aws cloudtrail start-query`.
