# S3 Transfer Acceleration Cost and Speed Reference

Load this reference when planning an S3 Transfer Acceleration
operation. The tables below show pricing by source region, speed
comparison methodology, and Direct Connect crossover thresholds.

## Acceleration pricing by source edge location

| Source region | Rate per GB (data IN) | Rate per GB (data OUT) |
|---|---|---|
| North America (to NA edge) | $0.004 | $0.004 |
| Europe (to EU edge) | $0.004 | $0.004 |
| Asia Pacific (to APAC edge) | $0.025 | $0.025 |
| South America | $0.025 | $0.025 |
| Australia / New Zealand | $0.025 | $0.025 |
| Africa | $0.025 | $0.025 |
| Middle East | $0.025 | $0.025 |

**Key:** the rate depends on the EDGE LOCATION nearest the uploader,
not the destination bucket region. An uploader in Tokyo sending to a
us-east-1 bucket pays $0.025/GB (APAC edge rate). An uploader in
London sending to the same us-east-1 bucket pays $0.004/GB (EU edge
rate).

## Cost calculation examples

| Scenario | Volume | Source region | Rate | Acceleration cost |
|---|---|---|---|---|
| Single 10 GB upload | 10 GB | Tokyo (APAC) | $0.025 | $0.25 |
| Single 10 GB upload | 10 GB | London (EU) | $0.004 | $0.04 |
| 1 TB migration | 1,024 GB | Sao Paulo (SA) | $0.025 | $25.60 |
| 50 TB migration | 51,200 GB | Tokyo (APAC) | $0.025 | $1,280.00 |
| 100 TB migration | 102,400 GB | London (EU) | $0.004 | $409.60 |
| 100 TB migration | 102,400 GB | Tokyo (APAC) | $0.025 | $2,560.00 |
| Daily 5 GB upload x 30 days | 150 GB | Singapore (APAC) | $0.025 | $3.75/month |

## Direct Connect crossover analysis

Direct Connect provides a dedicated network connection from your data
center to AWS. The crossover point where Direct Connect becomes
cheaper than Transfer Acceleration depends on monthly volume and
source region.

| Monthly volume | APAC acceleration cost | DC 1 Gbps total cost | DC 10 Gbps total cost | Cheaper option |
|---|---|---|---|---|
| 10 TB | $256 | $219 + $204 = $423 | $219 + $204 = $423 | Acceleration |
| 25 TB | $640 | $219 + $510 = $729 | $219 + $510 = $729 | Acceleration (marginal) |
| 50 TB | $1,280 | $219 + $1,020 = $1,239 | $219 + $1,020 = $1,239 | Direct Connect |
| 100 TB | $2,560 | $219 + $2,040 = $2,259 | $219 + $2,040 = $2,259 | Direct Connect |
| 200 TB | $5,120 | $219 + $4,080 = $4,299 | $219 + $4,080 = $4,299 | Direct Connect |

**Direct Connect cost model:**
- Port hourly rate: $0.30/hr (1 Gbps) = ~$219/month
- Data transfer out (DC to S3): $0.02/GB (varies by DX location)
- Data transfer in (S3 to DX): $0.00/GB (free in most cases)

**Crossover thresholds (approximate):**
- APAC source: ~45-50 TB/month — Direct Connect becomes cheaper
- EU/NA source: ~120+ TB/month — Direct Connect becomes cheaper
- One-time migration: Transfer Acceleration is almost always simpler
  (no infrastructure to provision)

## Speed comparison methodology

The S3 Transfer Acceleration speed comparison tool tests both
endpoints from the uploader's location:

```
https://s3-accelerate-speedtest.s3-accelerate.amazonaws.com/en/accelerate-speed-comparsion.html
```

**What it measures:**
1. Uploads small test files via the direct S3 endpoint (latency-bound)
2. Uploads the same files via the accelerate endpoint (edge-routed)
3. Reports throughput for each and the speedup factor

**When to expect speedup:**
| Source to destination | Expected speedup | Reason |
|---|---|---|
| Asia to US | 3-10x | High public internet latency; edge routing bypasses congested paths |
| South America to EU | 3-8x | Limited direct peering; edge uses optimized backbone |
| Europe to US | 1.5-3x | Moderate existing peering; edge adds marginal benefit |
| Same region (US to US) | 0.8-1.2x | No benefit; edge adds a hop |
| Same continent (EU to EU) | 0.9-1.1x | No benefit; edge adds a hop |

**When NOT to use acceleration:**
- Source and destination are in the same region
- Source and destination are on the same continent with good peering
- Transfer volume is small (< 1 GB) — the DNS resolution overhead
  exceeds the speed benefit
- The uploader is already on the AWS backbone (EC2 to S3 in the same
  region)

## CloudWatch metrics for monitoring

| Metric | What it measures | How to use |
|---|---|---|
| `BytesUploaded` (S3) | Total bytes uploaded to the bucket | Compare accelerate vs standard endpoint traffic |
| `4xxErrors` (S3) | Client errors per 1,000 requests | Spike after disable indicates clients still using accelerate endpoint |
| `FirstByteLatency` (S3) | Time to first byte | Lower with acceleration for distant uploaders |
| `TotalRequestLatency` (S3) | Full request latency | Lower with acceleration for distant uploaders |

```bash
# Monitor acceleration usage via CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name BytesUploaded \
  --dimensions Name=BucketName,Value=prod-data-lake \
  --start-time $(date -u -v-1h +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum \
  --profile default
```

## Diagnostic command quick-reference

| Goal | Command |
|---|---|
| Get acceleration config | `aws s3api get-bucket-accelerate-configuration --bucket <name>` |
| Enable acceleration | `aws s3api put-bucket-accelerate-configuration --bucket <name> --accelerate-configuration Status=Enabled` |
| Disable acceleration | `aws s3api put-bucket-accelerate-configuration --bucket <name> --accelerate-configuration Status=Suspended` |
| List multipart uploads | `aws s3api list-multipart-uploads --bucket <name>` |
| Abort multipart upload | `aws s3api abort-multipart-upload --bucket <name> --key <key> --upload-id <id>` |
| Test accelerate endpoint | `aws s3 ls s3://<name>/ --endpoint-url https://<name>.s3-accelerate.amazonaws.com` |
| Speed comparison tool | Open: `https://s3-accelerate-speedtest.s3-accelerate.amazonaws.com/en/accelerate-speed-comparsion.html` |
| CloudWatch metrics | `aws cloudwatch get-metric-statistics --namespace AWS/S3 --metric-name BytesUploaded ...` |
