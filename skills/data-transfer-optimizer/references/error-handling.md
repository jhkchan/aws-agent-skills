# Error Handling (load on demand) — Data Transfer Optimizer

CLI and data-source failure tables plus remediation guidance per opportunity
dimension moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling — CLI and data-source failures (moved from SKILL.md)



The workflow depends on three live data sources (Cost Explorer, VPC
API, service-specific APIs). Each can fail independently.

### Cost Explorer failures

| Failure mode | Detection | Handling |
|---|---|---|
| `AccessDeniedException` for `ce:GetCostAndUsage` | Exit code non-zero | Role lacks billing permissions. Proceed without CE; flag the gap. Operator grants `ce:GetCostAndUsage` and re-runs. |
| CE returns no data-transfer line items | Empty Results | Account has no data transfer in window, OR CE API is filtering by linked account. Check `--filter` for linked-account scope. |
| CE cost disagrees with CloudWatch metric volume | Cross-source mismatch | Trust CE for billing, CloudWatch for operations. Delta is typically free tier, taxes, or SERVICE-level rounding. |
| CE returns very high cost on a service you don't recognize | Unknown USAGE_TYPE | Cross-reference USAGE_TYPE with AWS pricing docs. Some charges (e.g., CloudFront under "AmazonCloudFront" service) hide data transfer inside the line item. |

### VPC API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-nat-gateways` returns empty | Empty list | No NAT Gateways in region. Confirm by checking other regions. |
| `describe-vpc-endpoints` returns Gateway Endpoints only | No Interface Endpoints | Either no Interface Endpoints deployed, or scope mismatch. Default scope is `Cluster` (regional); check both. |
| `describe-transit-gateways` returns empty | Empty list | No TGW in region. Skip TGW dimension. |
| `describe-vpc-peering-connections` returns deleted peerings | `Code == deleted` | Filter to `active` status only. Deleted peerings don't affect current cost. |
| `AccessDeniedException` for `ec2:Describe*` | Exit code non-zero | Role lacks EC2 read permissions. Add `ec2:Describe*` to the policy. |

### Service-specific API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `rds describe-db-instances` returns empty | Empty list | No RDS in region. Skip RDS dimension. |
| `directconnect describe-connections` returns empty | Empty list | No DX in use. Skip DX dimension. |
| `s3api get-bucket-location` errors with `NoSuchBucket` | API error | Bucket was deleted between list and location query. Skip that bucket. |
| `s3api get-bucket-replication` returns empty config | `Replication == {}` | No CRR configured. Skip CRR dimension. |
| CloudWatch NAT Gateway metric returns no datapoints | Empty Datapoints | NAT Gateway is < 24h old, or had no traffic. Re-query later. |

### Aggregate behavior

If ANY data source fails with a transient error (throttling,
network), retry up to 3 times with exponential backoff before
treating that dimension as NEED_MORE_INFO. For persistent failures
(IAM denial, missing service), emit the appropriate gating verdict
for that dimension and proceed with the remaining dimensions.



## Remediation guidance (moved from SKILL.md)



### For OPPORTUNITY_FOUND — NAT Gateway (add Gateway Endpoints)

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.s3 \
  --route-table-ids <rtb-1> <rtb-2> <rtb-3> \
  --vpc-endpoint-type Gateway \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=s3-gateway-endpoint}]"

aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.dynamodb \
  --route-table-ids <rtb-1> <rtb-2> <rtb-3> \
  --vpc-endpoint-type Gateway
```

No application changes required. Gateway Endpoints intercept S3 and
DynamoDB DNS automatically.

### For OPPORTUNITY_FOUND — NAT Gateway (add Interface Endpoint)

```bash
# Only recommend if break-even analysis favors Interface Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.sqs \
  --vpc-endpoint-type Interface \
  --subnet-ids <subnet-1a> <subnet-1b> <subnet-1c> \
  --security-group-ids <sg-private> \
  --private-dns-enabled
```

### For OPPORTUNITY_FOUND — Cross-AZ (AZ-pinning)

```bash
# Update ASG launch template subnet filter to single-AZ
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name <asg-name> \
  --vpc-zone-identifier "subnet-1a"  # was "subnet-1a,subnet-1b,subnet-1c"

# Create standby ASG in 1b for failover
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name <asg-name>-standby-1b \
  --launch-template <lt> \
  --vpc-zone-identifier "subnet-1b" \
  --min-size 0 --max-size 3 --desired-capacity 0
```

### For OPPORTUNITY_FOUND — Internet egress (CloudFront)

Route to `cloudfront-cost-optimizer` for the CloudFront-specific
optimization. The data-transfer-optimizer skill identifies the
opportunity and hands off.

### For OPPORTUNITY_FOUND — VPC topology (TGW → peering)

```bash
# Create peering connections for the full mesh
for src_vpc in $VPC_LIST; do
  for dst_vpc in $VPC_LIST; do
    if [ "$src_vpc" \< "$dst_vpc" ]; then
      aws ec2 create-vpc-peering-connection \
        --vpc-id $src_vpc --peer-vpc-id $dst_vpc
      # Accept the peering (if cross-account, requester accepts)
      aws ec2 accept-vpc-peering-connection \
        --vpc-peering-connection-id <pcx-id>
    fi
  done
done

# Update route tables to use peerings
# Then remove TGW attachments
aws ec2 delete-transit-gateway-vpc-attachment \
  --transit-gateway-attachment-id <tgw-attach-id>
```

### For OPPORTUNITY_FOUND — RDS migration

Multi-step: use `aws rds create-db-cluster` for Aurora, `aws dms
create-replication-task` for migration. Outside the scope of a
single skill invocation — hand off to the database team.

### For OPPORTUNITY_FOUND — Direct Connect

Provisioning DX is a multi-week physical-layer process (LOA, cross
connect, BGP configuration). Hand off to the network team for
provisioning; this skill sizes the commitment.

### For ALREADY_OPTIMAL or OPTIMIZED

1. No remediation required for the current posture.
2. Recommend monthly review of CUR data-transfer line items.
3. Re-evaluate Direct Connect upgrade at the next bandwidth
   forecast review.


