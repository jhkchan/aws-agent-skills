# Worked Examples — VPC Lattice Service Deployer

Deep reference content moved verbatim from `vpclattice-service-deployer/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Step 1 — create service network CLI

```bash
SN_ID=$(aws vpc-lattice create-service-network \
  --name my-service-network \
  --auth-type AWS_IAM \
  --tags source=skill-deploy \
  --query 'id' --output text)
echo "Service Network: $SN_ID"
```

## Step 3 — create service CLI

```bash
SVC_ID=$(aws vpc-lattice create-service \
  --name payments-svc \
  --query 'id' --output text)

echo "Service: $SVC_ID"
echo "Service DNS: $(aws vpc-lattice get-service \
  --service-identifier "$SVC_ID" \
  --query 'dnsEntry.domainName' --output text)"
```

## Step 7 — service network VPC association CLI

```bash
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SN_ID" \
  --vpc-identifier vpc-aaa11122

# Verify association status
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SN_ID" \
  --query 'items[*].{VPC:vpcId,Status:status}' --output table
# Expected: ACTIVE
```

## Step 9 — custom domain mapping CLI

```bash
# Associate custom domain with the service
aws vpc-lattice associate-custom-domain \
  --service-identifier "$SVC_ID" \
  --domain-name payments.internal.example.com \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/aaa-bbb-ccc

# Create Route 53 CNAME pointing to the service DNS
SERVICE_DNS=$(aws vpc-lattice get-service \
  --service-identifier "$SVC_ID" \
  --query 'dnsEntry.domainName' --output text)

aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch '{"Changes":[{"Action":"CREATE","ResourceRecordSet":{"Name":"payments.internal.example.com","Type":"CNAME","TTL":60,"ResourceRecords":[{"Value":"'$SERVICE_DNS'"}]}}]}'
```
