# Worked Examples — VPC Peering Deployer

Deep reference content moved verbatim from `vpc-peering-deployer/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Step 4 — create/accept CLI walkthroughs (same-account, cross-account, inter-region)

**Same-account, same-region:**

```bash
# Requester creates the peering connection
PCX_ID=$(aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-aaa11122 \
  --peer-vpc-id vpc-bbb22233 \
  --region us-east-1 \
  --query 'VpcPeeringConnection.VpcPeeringConnectionId' --output text)

echo "Peering connection: $PCX_ID"

# Accepter accepts (same account — can be immediate)
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id "$PCX_ID" \
  --region us-east-1
```

**Cross-account, same-region:**

```bash
# Requester creates the peering connection (specify peer owner ID)
PCX_ID=$(aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-aaa11122 \
  --peer-vpc-id vpc-bbb22233 \
  --peer-owner-id 999999999999 \
  --region us-east-1 \
  --query 'VpcPeeringConnection.VpcPeeringConnectionId' --output text)

# Accepter accepts (in the accepter account — different credentials)
# Either: assume a role in the accepter account, or have the accepter
# operator run this in their account:
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id "$PCX_ID" \
  --region us-east-1
```

**Inter-region (cross-region):**

```bash
# Requester creates the peering connection (specify peer region)
PCX_ID=$(aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-aaa11122 \
  --peer-vpc-id vpc-bbb22233 \
  --peer-owner-id 999999999999 \
  --peer-region us-west-2 \
  --region us-east-1 \
  --query 'VpcPeeringConnection.VpcPeeringConnectionId' --output text)

# Accepter accepts (in the accepter's region)
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id "$PCX_ID" \
  --region us-west-2
```

**Verify the connection is ACTIVE:**

```bash
aws ec2 describe-vpc-peering-connections \
  --vpc-peering-connection-ids "$PCX_ID" \
  --query 'VpcPeeringConnections[0].Status' --region us-east-1
# Expected: { Code: "active", Message: "Active" }
```
