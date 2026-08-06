# Eval prompt: loa-stale-requested

Audit the following Direct Connect topology for resilience and security
posture. Emit the standard VERDICT block (CONNECTION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Direct Connect topology for account 111111111111 (region us-east-1):

Connections (aws directconnect describe-connections):

```json
[
  {
    "connectionId": "dxcon-loa-stale-requested-primary",
    "connectionName": "primary",
    "connectionState": "available",
    "bandwidth": "10Gbps",
    "location": "EqSE2",
    "region": "us-east-1",
    "lagId": null,
    "connectionMode": "standard",
    "macSecCapable": true,
    "encryptionMode": "must_encrypt"
  },
  {
    "connectionId": "dxcon-loa-stale-requested-backup",
    "connectionName": "backup",
    "connectionState": "available",
    "bandwidth": "10Gbps",
    "location": "EqDC2",
    "region": "us-east-1",
    "lagId": null,
    "connectionMode": "standard",
    "macSecCapable": true,
    "encryptionMode": "must_encrypt"
  },
  {
    "connectionId": "dxcon-loa-stale-requested-tertiary",
    "connectionName": "tertiary-expansion",
    "connectionState": "requested",
    "bandwidth": "10Gbps",
    "location": "EqDA1",
    "region": "us-east-1",
    "lagId": null,
    "connectionMode": "standard",
    "macSecCapable": true,
    "encryptionMode": "must_encrypt",
    "loaIssueStatus": "stale - 6 business days in requested state, no LOA-CFA issued",
    "loaIssuedAt": null
  }
]
```

Virtual interfaces (aws directconnect describe-virtual-interfaces):

```json
[
  {
    "virtualInterfaceId": "dxvif-private-1",
    "virtualInterfaceType": "private",
    "connectionId": "dxcon-loa-stale-requested-primary",
    "vlan": 101,
    "bgpPeers": [{"asn": 64500, "bgpStatus": "up", "authKeyState": "configured"}]
  },
  {
    "virtualInterfaceId": "dxvif-private-2",
    "virtualInterfaceType": "private",
    "connectionId": "dxcon-loa-stale-requested-backup",
    "vlan": 102,
    "bgpPeers": [{"asn": 64500, "bgpStatus": "up", "authKeyState": "configured"}]
  }
]
```

Direct Connect Gateway: dxgw-prod (both VIFs attached)
