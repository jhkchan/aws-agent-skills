# Diagnostic and Verification Commands - vpn-connection-deployer

## Step 3 - download the customer-side configuration (moved from SKILL.md)

**Download the customer-side configuration** (IPSec parameters for the
on-prem device, vendor-specific):

```bash
aws ec2 describe-vpn-connections --vpn-connection-ids "$VPN_ID" \
  --output text \
  --query 'VpnConnections[0].CustomerGatewayConfiguration' \
  --region us-east-1 > customer-config.xml
```

**Critical:** tunnels stay DOWN until the customer device loads this
configuration and initiates. AWS cannot bring tunnels UP unilaterally.

## Step 6 - verify both tunnels are UP (moved from SKILL.md)

**Verify both tunnels are UP:**

```bash
aws ec2 describe-vpn-connections --vpn-connection-ids "$VPN_ID" \
  --query 'VpnConnections[0].VgwTelemetry' \
  --region us-east-1 --output table
# Expected: both tunnels show Status "up"
```

## Step 7 - CloudWatch monitoring setup (moved from SKILL.md)

| Metric | What it means | Alert threshold |
|---|---|---|
| `TunnelState` | 1 = UP, 0 = DOWN | Alert if < 1 for > 5 min |
| `TunnelDataIn` | Bytes inbound on the tunnel | Baseline + anomaly |
| `TunnelDataOut` | Bytes outbound on the tunnel | Baseline + anomaly |

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "vpn-${VPN_ID}-tunnel1-down" \
  --metric-name TunnelState --namespace AWS/VPN \
  --dimensions Name=VpnId,Value=$VPN_ID Name=TunnelIpAddress,Value=3.0.0.0 \
  --statistic Minimum --period 60 --evaluation-periods 5 \
  --threshold 1 --comparison-operator LessThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:vpn-alerts" \
  --region us-east-1
```

**Critical:** if TunnelState shows no data, the tunnel has never come
UP. Verify the customer device has loaded the configuration and the
IPSec parameters match.

## Step 9 - TGW VPN attachment association (moved from SKILL.md)

```bash
# VPN with TGW target (attachment created automatically)
VPN_ID=$(aws ec2 create-vpn-connection --type ipsec.1 \
  --customer-gateway-id "$CGW_ID" --transit-gateway-id "$TGW_ID" \
  --region us-east-1 \
  --query 'VpnConnection.VpnConnectionId' --output text)

# Find + associate the TGW VPN attachment
ATTACH_ID=$(aws ec2 describe-transit-gateway-attachments \
  --filters "Name=resource-id,Values=$VPN_ID" \
  --query 'TransitGatewayAttachments[0].TransitGatewayAttachmentId' \
  --output text --region us-east-1)

aws ec2 associate-transit-gateway-route-table \
  --transit-gateway-route-table-id tgw-rtb-aaa111 \
  --transit-gateway-attachment-id "$ATTACH_ID" --region us-east-1
```

**Critical:** TGW VPN attachments propagate routes via TGW route
tables. Enable route propagation on the TGW route table for the VPN
attachment's routes to be visible.
