# VPC Endpoint and NAT Gateway Pricing Reference

Supplementary reference for the NAT Gateway Cost Optimizer skill. Loaded
on-demand when break-even maths needs the detailed pricing matrix, Interface
endpoint service catalogue, or NAT Instance instance-type comparison.

## NAT Gateway pricing (us-east-1, 2026)

| Component | Rate | Monthly (730h) | Notes |
|---|---|---|---|
| Base hourly | $0.045/hour | $32.85 | Per gateway, billed continuously |
| Data processing | $0.045/GB | varies | Per GB processed through the gateway |

**Total monthly cost formula:**
```
monthly_cost = (num_gateways × $32.85) + (total_GB × $0.045)
```

**Examples:**
- 1 gateway, 100 GB/month: $32.85 + $4.50 = $37.35
- 1 gateway, 1 TB/month: $32.85 + $45.00 = $77.85
- 3 gateways (multi-AZ), 1 TB/month: $98.55 + $45.00 = $143.55
- 3 gateways (multi-AZ), 5 TB/month: $98.55 + $225.00 = $323.55

## Gateway VPC Endpoint pricing (FREE)

| Service | Service name | Hourly | Per-GB | Notes |
|---|---|---|---|---|
| Amazon S3 | `com.amazonaws.<region>.s3` | **$0.00** | **$0.00** | Route-table based; no ENI |
| Amazon DynamoDB | `com.amazonaws.<region>.dynamodb` | **$0.00** | **$0.00** | Route-table based; no ENI |

Gateway endpoints are unconditionally free. There is no break-even threshold.
The only cost is the operator time to create and maintain the endpoint policy.

## Interface VPC Endpoint pricing (us-east-1, 2026)

| Component | Rate | Monthly (730h) | Notes |
|---|---|---|---|
| Base hourly (per AZ) | $0.010/hour | $7.30 per AZ | One ENI per subnet (AZ) specified |
| Data processing (inbound) | $0.01/GB | varies | Per GB processed into the endpoint |

**Break-even formula (per service, per AZ count):**
```
break_even_GB = ($7.30 × num_AZs) / ($0.045 − $0.01)
             = ($7.30 × num_AZs) / $0.035
             = 208.6 × num_AZs  (approximately)
```

| Number of AZs | Break-even GB/month | Break-even TB/month |
|---|---|---|
| 1 | ~209 GB | ~0.2 TB |
| 2 | ~417 GB | ~0.4 TB |
| 3 | ~626 GB | ~0.6 TB |

**Rule of thumb:** use ~160 GB/month per AZ as a conservative threshold (accounts
for traffic variability and the $0.01/GB endpoint inbound cost net of the $0.045
NAT savings).

## Common Interface endpoint services (us-east-1 service names)

| Service | Service name suffix | Typical VPC traffic pattern | Break-even assessment |
|---|---|---|---|
| ECR API | `ecr.api` | Container image metadata | Evaluate alongside ecr.dkr |
| ECR Docker | `ecr.dkr` | Docker pull/push (large) | HIGH traffic candidate; usually above break-even for active clusters |
| SSM | `ssm` | Systems Manager agent | LOW — agents check in frequently but small payloads; usually skip |
| STS | `sts` | AssumeRole API calls | LOW — small payloads, high frequency; evaluate by call volume |
| Secrets Manager | `secretsmanager` | Secret fetches | LOW unless high-frequency rotation; evaluate |
| CloudWatch Logs | `logs` | Log shipping | MEDIUM-HIGH if logs are verbose; evaluate by log volume |
| CloudWatch Metrics | `monitoring` | Custom metric puts | LOW-MEDIUM; evaluate |
| KMS | `kms` | Encrypt/decrypt API | LOW — small payloads; usually skip |
| CodeArtifact API | `codeartifact.api` | Package pulls | MEDIUM; evaluate by CI volume |
| CodeArtifact Repositories | `codeartifact.repositories` | Package downloads | MEDIUM; evaluate by CI volume |
| API Gateway (private) | `execute-api` | Private API calls | Evaluate by API traffic |
| Kinesis Streams | `kinesis-streams` | Stream puts/gets | HIGH if streaming data; evaluate |
| Elastic Load Balancing | `elasticloadbalancing` | API calls only | LOW; skip |
| Auto Scaling | `autoscaling` | API calls only | LOW; skip |

## NAT Instance comparison (dev/test alternative)

| Instance type | Hourly (us-east-1) | Monthly (730h) | Bandwidth (approx) | Notes |
|---|---|---|---|---|
| t3.micro | $0.0104 | $7.59 | ~1 Gbps (burst) | Cheapest; minimal bandwidth |
| t3.small | $0.0208 | $15.18 | ~2 Gbps (burst) | Better for moderate dev traffic |
| t3.medium | $0.0416 | $30.37 | ~5 Gbps (with ENA) | Approaches NAT Gateway base cost |
| t4g.micro (Graviton) | $0.0084 | $6.13 | ~1 Gbps | Cheaper than t3.micro; ARM AMI required |

**NAT Instance savings vs NAT Gateway (per month):**
```
saving = (NAT_Gateway_base + NAT_data_processing) − NAT_Instance_monthly
       = ($32.85 + GB × $0.045) − $instance_monthly
```

For t3.micro at 1 TB/month NAT traffic:
- NAT Gateway cost: $32.85 + $45.00 = $77.85
- NAT Instance cost: $7.59 (flat)
- Saving: $70.26/month

**Reliability trade-off:** NAT Instance is a single EC2 host — no SLA, no HA,
bandwidth capped by instance type. Suitable ONLY for dev/test where an outage
is tolerable. Production workloads MUST use NAT Gateway.

## Cross-AZ data transfer pricing

| Direction | Rate | Notes |
|---|---|---|
| Within the same AZ | $0.00 | Free |
| Cross-AZ (each direction) | $0.01/GB | Applies to traffic crossing an AZ boundary |

**Impact on single-NAT topology:** if a private subnet in AZ-B sends traffic
to a NAT Gateway in AZ-A, the traffic crosses the AZ boundary. The cost is
`$0.01/GB` for the outbound leg and `$0.01/GB` for the return leg (NAT response
back to the source in AZ-B) — total `$0.02/GB` round-trip.

**Single-NAT vs multi-NAT decision (cross-AZ cost model):**
```
single_NAT_cost  = $32.85 + (total_GB × $0.045) + (cross_AZ_GB × $0.02)
multi_NAT_cost   = ($32.85 × num_AZs) + (total_GB × $0.045)

single_is_cheaper when: cross_AZ_GB × $0.02 < ($32.85 × (num_AZs − 1))
                    i.e., cross_AZ_GB < ($32.85 × (num_AZs − 1)) / $0.02
                    i.e., cross_AZ_GB < 1642 × (num_AZs − 1)
```

For a 3-AZ VPC: single-NAT is cheaper if cross-AZ traffic < 3,285 GB/month.
For a 2-AZ VPC: single-NAT is cheaper if cross-AZ traffic < 1,642 GB/month.

## Regional pricing variance (sample regions)

| Region | NAT Gateway base $/hr | NAT data $/GB | Interface endpoint $/hr/AZ | Notes |
|---|---|---|---|---|
| us-east-1 (N. Virginia) | 0.045 | 0.045 | 0.010 | Baseline |
| us-west-2 (Oregon) | 0.045 | 0.045 | 0.010 | Same as us-east-1 |
| eu-west-1 (Ireland) | 0.0495 | 0.0495 | 0.011 | ~10% premium |
| eu-central-1 (Frankfurt) | 0.054 | 0.054 | 0.012 | ~20% premium |
| ap-southeast-1 (Singapore) | 0.054 | 0.054 | 0.012 | ~20% premium |
| ap-southeast-2 (Sydney) | 0.0585 | 0.0585 | 0.013 | ~30% premium |
| ap-northeast-1 (Tokyo) | 0.054 | 0.054 | 0.012 | ~20% premium |
| ap-south-1 (Mumbai) | 0.0585 | 0.0585 | 0.013 | ~30% premium |
| sa-east-1 (São Paulo) | 0.072 | 0.072 | 0.016 | ~60% premium |

**Decision impact:** in high-premium regions (sa-east-1, ap-southeast-2),
the savings from Gateway endpoints are LARGER (because the per-GB NAT cost is
higher). Be MORE aggressive with Interface endpoint recommendations in these
regions — the break-even threshold is lower in GB terms.

Always re-state the regional rate in the SAVINGS block when the VPC is not in
us-east-1.

## Cost baseline (us-east-1, 2026) — moved from SKILL.md

**Cost baseline (us-east-1, 2026):**

| Component | Rate | Notes |
|---|---|---|
| NAT Gateway base | $0.045/hour (~$32.85/month) | Per gateway, billed regardless of traffic |
| NAT Gateway data processing | $0.045/GB | The multiplier — 1 TB = $45/month on top of base |
| Gateway VPC Endpoint (S3, DynamoDB) | **FREE** | No hourly, no per-GB, no AZ surcharge |
| Interface VPC Endpoint base | $0.01/hour per AZ (~$7.30/month per AZ) | Billed per ENI across AZs where the endpoint exists |
| Interface VPC Endpoint data | $0.01/GB | Inbound to the endpoint from the VPC |
| Cross-AZ data transfer | $0.01/GB (each direction) | Applies when traffic crosses an AZ boundary |
| NAT Instance (t3.micro) | ~$8.47/month (t3.micro, 730h × $0.0116) | Fixed cost, no per-GB; bandwidth ~1 Gbps, not HA |
