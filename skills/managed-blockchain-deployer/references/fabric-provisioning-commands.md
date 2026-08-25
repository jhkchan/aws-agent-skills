# Fabric Provisioning CLI Commands — Managed Blockchain Deployer

Full copy-pasteable CLI command sequence for provisioning AWS
Managed Blockchain Hyperledger Fabric networks, members, peer nodes,
certificate authority enrollment, channels, and chaincode. Variables
to substitute: `<network-id>`, `<member-id>`, `<node-id>`,
 `<region>`, `<az>`, `<admin-user>`, `<admin-pass>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm VPC subnets in target AZ
aws ec2 describe-subnets \
  --filters "Name=availability-zone,Values=us-east-1a" \
  --query 'Subnets[*].SubnetId' --output table

# Confirm Fabric CA client is installed
fabric-ca-client version

# Confirm peer CLI is installed
peer version
```

## Step 1: Create the Fabric network (Standard edition) + founder member

```bash
NETWORK_ID=$(aws managedblockchain create-network \
  --name "consortium-supply-chain" \
  --description "Supply chain tracking consortium" \
  --framework HYPERLEDGER_FABRIC \
  --framework-version "2.2" \
  --network-configuration '{"Edition": "STANDARD"}' \
  --voting-policy '{
    "ApprovalThresholdPolicy": {
      "ThresholdPercentage": 50,
      "ProposalDurationInHours": 24,
      "ThresholdComparator": "GREATER_THAN"
    }
  }' \
  --member-configuration '{
    "Name": "founder-member",
    "FrameworkConfiguration": {
      "Fabric": {"AdminUsername": "admin", "AdminPassword": "Admin12345!"}
    }
  }' \
  --region us-east-1 \
  --query NetworkId --output text)

echo "Network ID: $NETWORK_ID"
# Founder member ID is returned in the same response
MEMBER_ID=$(aws managedblockchain list-members \
  --network-id "$NETWORK_ID" \
  --region us-east-1 \
  --query 'Members[0].Id' --output text)
echo "Member ID: $MEMBER_ID"
```

## Step 2: Wait for member + CA to become AVAILABLE

```bash
# Poll member status until AVAILABLE (typically 10-15 min)
aws managedblockchain get-member \
  --network-id "$NETWORK_ID" \
  --member-id "$MEMBER_ID" \
  --region us-east-1 \
  --query 'Member.Status' --output text
# Expected: AVAILABLE

# Retrieve CA endpoint
CA_ENDPOINT=$(aws managedblockchain get-member \
  --network-id "$NETWORK_ID" \
  --member-id "$MEMBER_ID" \
  --region us-east-1 \
  --query 'Member.FrameworkAttributes.Fabric.CaEndpoint' --output text)
echo "CA Endpoint: $CA_ENDPOINT"
```

## Step 3: Create a peer node

```bash
NODE_ID=$(aws managedblockchain create-node \
  --network-id "$NETWORK_ID" \
  --member-id "$MEMBER_ID" \
  --node-configuration '{
    "InstanceType": "bc.m5.large",
    "AvailabilityZone": "us-east-1a",
    "LogPublishingConfiguration": {
      "Fabric": {
        "ChaincodeLogs": {"CloudwatchLogsEnabled": true},
        "StateRequests": {"CloudwatchLogsEnabled": true},
        "Transactions": {"CloudwatchLogsEnabled": true}
      }
    }
  }' \
  --region us-east-1 \
  --query NodeId --output text)

echo "Node ID: $NODE_ID"
```

## Step 4: Wait for node to become AVAILABLE

```bash
# Poll node status until AVAILABLE (typically 10-20 min)
aws managedblockchain get-node \
  --network-id "$NETWORK_ID" \
  --node-id "$NODE_ID" \
  --region us-east-1 \
  --query 'Node.Status' --output text
# Expected: AVAILABLE
```

## Step 5: Download CA TLS certificate and enroll admin

```bash
# Download the TLS chain
aws s3 cp \
  s3://us-east-1.managedblockchain/etc/managed-blockchain-tls-chain.pem \
  ./managed-blockchain-tls-chain.pem

# Enroll the admin identity
fabric-ca-client enroll \
  -u "https://admin:Admin12345!@${CA_ENDPOINT}" \
  --tls.certfiles ./managed-blockchain-tls-chain.pem \
  -M ./admin-msp
```

## Step 6: Set peer environment and create a channel

```bash
export CORE_PEER_ADDRESS=$(aws managedblockchain get-node \
  --network-id "$NETWORK_ID" \
  --node-id "$NODE_ID" \
  --region us-east-1 \
  --query 'Node.FrameworkAttributes.Fabric.PeerEndpoint' --output text)
export CORE_PEER_LOCALMSPID="${MEMBER_ID}MSP"
export CORE_PEER_MSPCONFIGPATH=./admin-msp
export CORE_PEER_TLS_ROOTCERT_FILE=./managed-blockchain-tls-chain.pem

# Generate channel config transaction
configtxgen -profile OneOrgChannel \
  -channelID supply-chain-channel \
  -outputCreateChannelTx ./channel.tx

# Create the channel
peer channel create \
  -c supply-chain-channel \
  -f ./channel.tx \
  -o $ORDERER_ENDPOINT \
  --tls --cafile ./managed-blockchain-tls-chain.pem

# Join the peer to the channel
peer channel join -b supply-chain-channel.block
```

## Step 7: Install and commit chaincode (Fabric 2.x lifecycle)

```bash
# Package
peer lifecycle chaincode package supply-chain-cc.tar.gz \
  --path github.com/example/supply-chain \
  --lang golang \
  --label supply-chain-cc_1.0

# Install
peer lifecycle chaincode install supply-chain-cc.tar.gz

# Get the package ID
PACKAGE_ID=$(peer lifecycle chaincode queryinstalled \
  --output json | jq -r '.installed_chaincodes[0].package_id')

# Approve for org
peer lifecycle chaincode approveformyorg \
  -C supply-chain-channel \
  -n supply-chain-cc -v 1.0 \
  --package-id "$PACKAGE_ID" --sequence 1 \
  --tls --cafile ./managed-blockchain-tls-chain.pem

# Check commit readiness
peer lifecycle chaincode checkcommitreadiness \
  -C supply-chain-channel \
  -n supply-chain-cc -v 1.0 --sequence 1 \
  --tls --cafile ./managed-blockchain-tls-chain.pem

# Commit
peer lifecycle chaincode commit \
  -C supply-chain-channel \
  -n supply-chain-cc -v 1.0 --sequence 1 \
  --tls --cafile ./managed-blockchain-tls-chain.pem
```

## Step 8: Invite additional members (consortium governance)

```bash
# Founder submits proposal to invite a new member account
PROPOSAL_ID=$(aws managedblockchain create-proposal \
  --network-id "$NETWORK_ID" \
  --member-id "$MEMBER_ID" \
  --actions '{"Invitations": [{"Principal": "123456789012"}]}' \
  --region us-east-1 \
  --query ProposalId --output text)

# Members vote on the proposal
aws managedblockchain vote-on-proposal \
  --network-id "$NETWORK_ID" \
  --proposal-id "$PROPOSAL_ID" \
  --member-id "$MEMBER_ID" \
  --vote YES --region us-east-1
```

## Verification

```bash
# Network status
aws managedblockchain get-network \
  --network-id "$NETWORK_ID" --region us-east-1

# Member status + CA endpoint
aws managedblockchain get-member \
  --network-id "$NETWORK_ID" \
  --member-id "$MEMBER_ID" --region us-east-1

# Node status + endpoints
aws managedblockchain get-node \
  --network-id "$NETWORK_ID" \
  --node-id "$NODE_ID" --region us-east-1

# List all nodes for the member
aws managedblockchain list-nodes \
  --network-id "$NETWORK_ID" \
  --member-id "$MEMBER_ID" --region us-east-1

# List all members
aws managedblockchain list-members \
  --network-id "$NETWORK_ID" --region us-east-1
```

## Terraform equivalent

```hcl
resource "aws_managedblockchain_network" "fabric" {
  name                = "consortium-supply-chain"
  description         = "Supply chain tracking consortium"
  framework           = "HYPERLEDGER_FABRIC"
  framework_version   = "2.2"
  voting_policy {
    approval_threshold_policy {
      threshold_percentage       = 50
      proposal_duration_in_hours = 24
      threshold_comparator       = "GREATER_THAN"
    }
  }
  network_configuration {
    edition = "STANDARD"
  }
}

resource "aws_managedblockchain_member" "founder" {
  network_id     = aws_managedblockchain_network.fabric.id
  member_name    = "founder-member"
  description    = "Founder member"
  framework_configuration {
    fabric {
      admin_username = "admin"
      admin_password = "Admin12345!"
    }
  }
}

resource "aws_managedblockchain_node" "peer" {
  network_id     = aws_managedblockchain_network.fabric.id
  member_id      = aws_managedblockchain_member.founder.id
  node_type      = "PEER"
  instance_type  = "bc.m5.large"
  availability_zone = "us-east-1a"
  log_publishing_configuration {
    fabric {
      chaincdelogs      = true
      state_requests    = true
      transactions_logs = true
    }
  }
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Create network + founder member | `aws managedblockchain create-network` |
| Create member (invited) | `aws managedblockchain create-member` |
| Create proposal (invite) | `aws managedblockchain create-proposal` |
| Vote on proposal | `aws managedblockchain vote-on-proposal` |
| Create peer node | `aws managedblockchain create-node` |
| Get network | `aws managedblockchain get-network` |
| Get member | `aws managedblockchain get-member` |
| Get node | `aws managedblockchain get-node` |
| List members | `aws managedblockchain list-members` |
| List nodes | `aws managedblockchain list-nodes` |
| Delete node | `aws managedblockchain delete-node` |
| Delete member | `aws managedblockchain delete-member` |
| Delete network | `aws managedblockchain delete-network` |

---

## Step 5 — Certificate authority enrollment (moved verbatim from SKILL.md)

**Retrieve CA endpoint:**

```bash
aws managedblockchain get-member \
  --network-id n-ABCDEFGHIJ1234567 \
  --member-id m-ABCDEFGHIJ1234567 \
  --region us-east-1 \
  --query 'Member.FrameworkAttributes.Fabric.CaEndpoint' --output text
# Output: ca.m-xxxxxxxxxxxxx.n-xxxxxxxxxxxx.managedblockchain.us-east-1.amazonaws.com:30002
```

**Download the CA TLS certificate:**

```bash
aws s3 cp \
  s3://us-east-1.managedblockchain/etc/managed-blockchain-tls-chain.pem \
  ./managed-blockchain-tls-chain.pem
```

**Enroll the admin identity:**

```bash
fabric-ca-client enroll \
  -u https://admin:Admin12345!@ca.m-xxxxxxxxxxxxx.n-xxxxxxxxxxxx.managedblockchain.us-east-1.amazonaws.com:30002 \
  --tls.certfiles ./managed-blockchain-tls-chain.pem \
  -M ./admin-msp
```

This produces the admin MSP directory containing the enrollment
certificate (`cert.pem`), private key (`keystore/`), CA root cert
(`cacert.pem`), and TLS CA cert (`TLScacert.pem`). This admin cert
authorizes channel creation, chaincode install, and instantiation.

## Step 6 — Channel creation CLI (moved verbatim from SKILL.md)

```bash
export CORE_PEER_ADDRESS=nd-xxxxxxxxxxxxx.m-xxxxxxxxxxxxx.n-xxxxxxxxxxxx.managedblockchain.us-east-1.amazonaws.com:30003
export CORE_PEER_LOCALMSPID=m-ABCDEFGHIJ1234567MSP
export CORE_PEER_MSPCONFIGPATH=./admin-msp
export CORE_PEER_TLS_ROOTCERT_FILE=./managed-blockchain-tls-chain.pem

# Generate channel config transaction
configtxgen -profile OneOrgChannel -channelID supply-chain-channel -outputCreateChannelTx ./channel.tx

# Create the channel
peer channel create -c supply-chain-channel -f ./channel.tx \
  -o $ORDERER_ENDPOINT --tls --cafile ./managed-blockchain-tls-chain.pem

# Join the peer to the channel
peer channel join -b supply-chain-channel.block
```

## Step 7 — Chaincode lifecycle CLI (moved verbatim from SKILL.md)

**Fabric 1.4 (install + instantiate):**

```bash
peer chaincode install -n supply-chain-cc -v 1.0 -p github.com/example/supply-chain -l golang

peer chaincode instantiate -n supply-chain-cc -v 1.0 -C supply-chain-channel \
  -c '{"function":"init","Args":[]}' \
  -o $ORDERER_ENDPOINT --tls --cafile ./managed-blockchain-tls-chain.pem
```

**Fabric 2.x (approve + commit — new decentralized lifecycle):**

```bash
# Package
peer lifecycle chaincode package supply-chain-cc.tar.gz \
  --path github.com/example/supply-chain --lang golang --label supply-chain-cc_1.0

# Install
peer lifecycle chaincode install supply-chain-cc.tar.gz

# Approve for org
peer lifecycle chaincode approveformyorg -C supply-chain-channel \
  -n supply-chain-cc -v 1.0 --package-id $PACKAGE_ID --sequence 1 \
  --tls --cafile ./managed-blockchain-tls-chain.pem

# Commit (after enough orgs approve)
peer lifecycle chaincode commit -C supply-chain-channel \
  -n supply-chain-cc -v 1.0 --sequence 1 \
  --tls --cafile ./managed-blockchain-tls-chain.pem
```

