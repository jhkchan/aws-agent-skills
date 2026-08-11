# Routing Policy Change-Batch Examples — Route 53 Routing Policy Deployer

Reference change-batch JSON for each routing policy. Substitute
`<ZONE_ID>`, `<NAME>`, `<TARGET>`, `<HC_ID>`, `<REGION>`, `<WEIGHT>`,
`<LATENCY_REGION>`, `<CONTINENT>`, `<COUNTRY>`, `<BIAS>`, `<CIDR>`,
`<ALIAS_DNS>`, `<ALIAS_ZONE_ID>` as needed. Stored here so the main
skill body stays scannable.

## 1. Simple routing — single record

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "www.example.com.",
      "Type": "A",
      "TTL": 300,
      "ResourceRecords": [{"Value": "192.0.2.10"}]
    }
  }]
}
```

## 2. Weighted routing — 90/10 canary

Both records MUST be posted in the same change-batch (atomic). Each
record has a `HealthCheckId` — weighted without HC sends dead targets
their allotted percentage.

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "api.example.com.",
      "Type": "A",
      "SetIdentifier": "primary",
      "Weight": 90,
      "HealthCheckId": "<HC_ID_PRIMARY>",
      "TTL": 60,
      "ResourceRecords": [{"Value": "10.0.0.10"}]
    }
  },{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "api.example.com.",
      "Type": "A",
      "SetIdentifier": "canary",
      "Weight": 10,
      "HealthCheckId": "<HC_ID_CANARY>",
      "TTL": 60,
      "ResourceRecords": [{"Value": "10.0.0.20"}]
    }
  }]
}
```

## 3. Latency routing — multi-region active-active

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "api.example.com.",
      "Type": "A",
      "SetIdentifier": "use1",
      "Region": "us-east-1",
      "HealthCheckId": "<HC_ID_USE1>",
      "TTL": 60,
      "ResourceRecords": [{"Value": "10.0.0.10"}]
    }
  },{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "api.example.com.",
      "Type": "A",
      "SetIdentifier": "usw2",
      "Region": "us-west-2",
      "HealthCheckId": "<HC_ID_USW2>",
      "TTL": 60,
      "ResourceRecords": [{"Value": "10.0.0.20"}]
    }
  }]
}
```

## 4. Failover routing — PRIMARY / SECONDARY with HC

PRIMARY MUST reference a health check. When PRIMARY is unhealthy,
Route 53 returns SECONDARY. `EvaluateTargetHealth` on alias targets
inside a failover set multiplies the check.

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "dr.example.com.",
      "Type": "A",
      "SetIdentifier": "primary",
      "Failover": "PRIMARY",
      "HealthCheckId": "<HC_ID_PRIMARY>",
      "TTL": 60,
      "ResourceRecords": [{"Value": "10.0.0.10"}]
    }
  },{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "dr.example.com.",
      "Type": "A",
      "SetIdentifier": "secondary",
      "Failover": "SECONDARY",
      "TTL": 60,
      "ResourceRecords": [{"Value": "10.0.0.20"}]
    }
  }]
}
```

## 5. Geolocation routing — continent + default

The default record (`Continent: "**"`) is mandatory to avoid NXDOMAIN
for unmatched regions.

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "geo.example.com.",
      "Type": "A",
      "SetIdentifier": "na",
      "GeoLocation": {"ContinentCode": "NA"},
      "TTL": 300,
      "ResourceRecords": [{"Value": "10.0.0.10"}]
    }
  },{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "geo.example.com.",
      "Type": "A",
      "SetIdentifier": "eu",
      "GeoLocation": {"ContinentCode": "EU"},
      "TTL": 300,
      "ResourceRecords": [{"Value": "10.0.0.20"}]
    }
  },{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "geo.example.com.",
      "Type": "A",
      "SetIdentifier": "default",
      "GeoLocation": {"CountryCode": "*"},
      "TTL": 300,
      "ResourceRecords": [{"Value": "10.0.0.30"}]
    }
  }]
}
```

## 6. Geoproximity routing — bias toward/away

Bias range is -99 to +99. Positive biases more traffic toward the
resource; negative biases away. Bias 0 = no effect.

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "flux.example.com.",
      "Type": "A",
      "SetIdentifier": "use1",
      "GeoProximityLocation": {"AWSRegion": "us-east-1", "Bias": 50},
      "TTL": 300,
      "ResourceRecords": [{"Value": "10.0.0.10"}]
    }
  },{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "flux.example.com.",
      "Type": "A",
      "SetIdentifier": "usw2",
      "GeoProximityLocation": {"AWSRegion": "us-west-2", "Bias": -50},
      "TTL": 300,
      "ResourceRecords": [{"Value": "10.0.0.20"}]
    }
  }]
}
```

## 7. Multivalue answer routing — round-robin with failover

Each value should reference a health check. Without HC, dead IPs stay
in client rotation for the TTL window.

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "pool.example.com.",
      "Type": "A",
      "SetIdentifier": "node-a",
      "MultiValueAnswer": true,
      "HealthCheckId": "<HC_ID_A>",
      "TTL": 30,
      "ResourceRecords": [{"Value": "10.0.0.10"}]
    }
  },{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "pool.example.com.",
      "Type": "A",
      "SetIdentifier": "node-b",
      "MultiValueAnswer": true,
      "HealthCheckId": "<HC_ID_B>",
      "TTL": 30,
      "ResourceRecords": [{"Value": "10.0.0.20"}]
    }
  }]
}
```

## 8. IP-based routing — CIDR blocks

Overlapping CIDRs evaluate in document order; first match wins. Order
matters — most-specific CIDR should come first.

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "cidr.example.com.",
      "Type": "A",
      "SetIdentifier": "office",
      "CidrRoutingConfig": {
        "CollectionConfigs": [{"LocationName": "office", "CidrList": ["203.0.113.0/24"]}]
      },
      "TTL": 300,
      "ResourceRecords": [{"Value": "10.0.0.10"}]
    }
  },{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "cidr.example.com.",
      "Type": "A",
      "SetIdentifier": "default",
      "CidrRoutingConfig": {
        "CollectionConfigs": [{"LocationName": "default", "CidrList": ["0.0.0.0/0"]}]
      },
      "TTL": 300,
      "ResourceRecords": [{"Value": "10.0.0.20"}]
    }
  }]
}
```

## 9. Alias record — to ALB with EvaluateTargetHealth

Alias records use `Type: A` (or `AAAA`), NOT `CNAME`. The alias target
DNS name has a trailing dot. `EvaluateTargetHealth: true` enables
DNS-level failover.

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "app.example.com.",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "<ALB_ZONE_ID>",
        "DNSName": "<ALB_DNS_NAME>.",
        "EvaluateTargetHealth": true
      }
    }
  }]
}
```

The ALB hosted zone ID is region-fixed (e.g., `Z35SXDOTRQ7X7K` for
us-east-1). Look it up with `aws elbv2 describe-load-balancers --query
'LoadBalancers[0].CanonicalHostedZoneId'`.

## 10. Alias record — to CloudFront distribution

CloudFront's hosted zone ID is `Z2FDTNDATAQYW2` for all distributions.

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "cdn.example.com.",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "Z2FDTNDATAQYW2",
        "DNSName": "d111111abcdef8.cloudfront.net.",
        "EvaluateTargetHealth": false
      }
    }
  }]
}
```

`EvaluateTargetHealth` is `false` for CloudFront — Route 53 does not
ingest CloudFront health, and the flag is silently ignored.

## 11. Alias record — to S3 website endpoint

The S3 website endpoint hosted zone ID is region-fixed (e.g.,
`Z3AQBSTLFOQMN4` for us-east-1). The bucket must have static website
hosting enabled.

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "www.example.com.",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "Z3AQBSTLFOQMN4",
        "DNSName": "www.example.com.s3-website-us-east-1.amazonaws.com.",
        "EvaluateTargetHealth": false
      }
    }
  }]
}
```

## 12. Alias record — to VPC interface endpoint

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "internal-api.example.com.",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "<VPCE_ZONE_ID>",
        "DNSName": "<VPCE_DNS_NAME>.",
        "EvaluateTargetHealth": false
      }
    }
  }]
}
```

`EvaluateTargetHealth` is `false` — VPC interface endpoints do not
expose health to Route 53.
