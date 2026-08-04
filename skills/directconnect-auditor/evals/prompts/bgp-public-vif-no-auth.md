# Eval prompt: bgp-public-vif-no-auth

Audit the following Direct Connect topology for resilience and security
posture. Emit the standard VERDICT block (CONNECTION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Direct Connect topology for account 111111111111 (region us-east-1):

Connections (aws directconnect describe-connections):

```json
[
  {
    "connectionId": "dxcon-bgp-public-vif-no-auth-primary",
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
    "connectionId": "dxcon-bgp-public-vif-no-auth-backup",
    "connectionName": "backup",
    "connectionState": "available",
    "bandwidth": "10Gbps",
    "location": "EqDC2",
    "region": "us-east-1",
    "lagId": null,
    "connectionMode": "standard",
    "macSecCapable": true,
    "encryptionMode": "must_encrypt"
  }
]
```

Virtual interfaces (aws directconnect describe-virtual-interfaces):

```json
[
  {
    "virtualInterfaceId": "dxvif-public-prod",
    "virtualInterfaceType": "public",
    "connectionId": "dxcon-bgp-public-vif-no-auth-primary",
    "vlan": 200,
    "customerAddress": "203.0.113.10/30",
    "amazonAddress": "203.0.113.9/30",
    "advertisedPrefixes": ["203.0.113.0/24"],
    "bgpPeers": [{"asn": 65000, "bgpStatus": "up", "authKey": null}]
  },
  {
    "virtualInterfaceId": "dxvif-private-backup",
    "virtualInterfaceType": "private",
    "connectionId": "dxcon-bgp-public-vif-no-auth-backup",
    "vlan": 101,
    "bgpPeers": [{"asn": 64500, "bgpStatus": "up", "authKey": null}]
  }
]
```

BGP peer authoritative state (aws directconnect describe-bgp-peers):

```json
[
  {
    "virtualInterfaceId": "dxvif-public-prod",
    "bgpPeerId": "bgp-public-1",
    "asn": 65000,
    "bgpStatus": "up",
    "authKeyState": "never-configured-at-creation"
  },
  {
    "virtualInterfaceId": "dxvif-private-backup",
    "bgpPeerId": "bgp-private-1",
    "asn": 64500,
    "bgpStatus": "up",
    "authKeyState": "configured"
  }
]
```

Direct Connect Gateway: dxgw-prod (private VIF attached)
