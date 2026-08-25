# Error Handling — Grafana Data Source Deployer

Failure-mode detail moved verbatim from SKILL.md.

## Error handling — moved from SKILL.md

### Data source returns empty results
- The workspace IAM role is missing per-service permissions. Verify
  the role has correct actions (e.g., `cloudwatch:GetMetricData`).
  Silent failure — no error in the Grafana UI.

### SAML login fails
- IdP metadata not configured or incorrect. Verify IdP metadata
  URL/XML. Check ACS URL matches `https://<workspace>/login/saml/acs`.

### Prometheus data source query fails
- AMP workspace URL incorrect or workspace role lacks
  `aps:QueryMetrics`. Verify data source URL and SigV4 config.

### Dashboard panels show "No data"
- Data source UID in dashboard JSON does not match workspace data
  source UID. Query the API for correct UIDs and update the JSON.

### API key authentication fails
- API key has expired. Create a new key with an appropriate TTL.
