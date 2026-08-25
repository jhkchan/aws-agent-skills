# Worked Examples - vpn-connection-deployer

## Worked example: TGW-attached VPN with BGP and IKEv2 (moved from SKILL.md)

```text
VPN_CONNECTION: vpn-111222333 — CGW cgw-aaa111 → TGW tgw-000111222333
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Customer Gateway: cgw-aaa111 (203.0.113.12, BGP ASN 65000)
  [✓] AWS-side target: TGW tgw-000111222333
  [✓] VPN connection: vpn-111222333 — two IPSec tunnels
  [✓] Routing: Dynamic BGP (ASN 64512 ↔ 65000)
  [✓] Tunnel 1: 3.221.215.181 — inside CIDR 169.254.10.0/30 — IKEv2
  [✓] Tunnel 2: 3.221.215.204 — inside CIDR 169.254.10.4/30 — IKEv2
  [✓] Phase 1: AES256 / SHA256 / DH group 17 / lifetime 28800s
  [✓] Phase 2: AES256 / SHA256 / PFS group 17 / lifetime 3600s
  [✓] DPD: timeout 30s, retries 3
  [✓] Redundancy: active-active (BGP ECMP)
  [✓] Route propagation: TGW route table tgw-rtb-aaa111
  [✓] CloudWatch: TunnelState alarm on arn:aws:sns:us-east-1:123456789012:vpn-alerts
  [✓] Acceleration: Disabled
  [✓] IPv6: IPv4 only
  [✓] Outside IP: public (203.0.113.12)
  [✓] Tags: Environment=production, Topology=onprem-to-tgw
VERIFICATION_COMMANDS:
  aws ec2 describe-vpn-connections --vpn-connection-ids vpn-111222333 --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/VPN --metric-name TunnelState --dimensions Name=VpnId,Value=vpn-111222333 --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T00:10:00Z --period 60 --statistics Minimum --region us-east-1
```
