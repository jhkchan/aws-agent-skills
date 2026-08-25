# Diagnostic commands — rds-instance-auditor (load on demand)

Moved verbatim from SKILL.md; load only when needed.

## Account-wide sweep (pagination)

```bash
token=""
while true; do
  if [ -z "$token" ]; then
    aws rds describe-db-instances --output json > page.json
  else
    aws rds describe-db-instances --output json --starting-token "$token" > page.json
  fi
  # Process page.json instances here
  token=$(jq -r '.Marker // empty' page.json)
  [ -z "$token" ] && break
done
# Aurora: fetch cluster metadata in a separate paginated call
aws rds describe-db-clusters --output json > clusters.json
```

