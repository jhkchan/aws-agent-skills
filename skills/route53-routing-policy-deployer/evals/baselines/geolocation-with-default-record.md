# Baseline (no-skill) — geolocation-with-default-record

> This is the response a model produces **without** the skill definition.
> It omits the default record, so clients from continents other than NA
> and EU get NXDOMAIN with no alarm. Generated for with-skill-vs-baseline
> comparison.

---

To set up geolocation routing:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z5DABCDEFGHIJK \
  --change-batch '{
    "Changes": [
      {"Action":"CREATE","ResourceRecordSet":{"Name":"geo.example.com.","Type":"A","SetIdentifier":"na","GeoLocation":{"ContinentCode":"NA"},"TTL":300,"ResourceRecords":[{"Value":"10.10.0.10"}]}},
      {"Action":"CREATE","ResourceRecordSet":{"Name":"geo.example.com.","Type":"A","SetIdentifier":"eu","GeoLocation":{"ContinentCode":"EU"},"TTL":300,"ResourceRecords":[{"Value":"10.20.0.20"}]}}
    ]
  }'
```

That routes NA and EU traffic to your regional IPs.
