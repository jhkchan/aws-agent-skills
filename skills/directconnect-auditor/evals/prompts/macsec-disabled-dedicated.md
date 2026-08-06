# Eval prompt: macsec-disabled-dedicated

Audit the following Direct Connect topology for resilience and security
posture. Emit the standard VERDICT block (CONNECTION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Direct Connect topology for account 111111111111 (region us-east-1):

Connections (aws directconnect describe-connections):

```json
[
  {
    "connectionId": "dxcon-macsec-disabled-dedicated-primary",
    "connectionName": "primary",
    "connectionState": "available",
    "bandwidth": "10Gbps",
    "location": "EqSE2",
    "region": "us-east-1",
    "lagId": null,
    "connectionMode": "standard",
    "macSecCapable": true,
    "encryptionMode": "no_encrypt"
  },
  {
    "connectionId": "dxcon-macsec-disabled-dedicated-backup",
    "connectionName": "backup",
    "connectionState": "available",
    "bandwidth": "10Gbps",
    "location": "EqDC2",
    "region": "us-east-1",
    "lagId": null,
    "connectionMode": "standard",
    "macSecCapable": true,
    "encryptionMode": "no_encrypt"
  }
]
```

Virtual interfaces (aws directconnect describe-virtual-interfaces):

```json
[
  {
    "virtualInterfaceId": "dxvif-private-1",
    "virtualInterfaceType": "private",
    "connectionId": "dxcon-macsec-disabled-dedicated-primary",
    "vlan": 101,
    "bgpPeers": [{"asn": 64500, "bgpStatus": "up", "authKeyState": "configured"}]
  },
  {
    "virtualInterfaceId": "dxvif-private-2",
    "virtualInterfaceType": "private",
    "connectionId": "dxcon-macsec-disabled-dedicated-backup",
    "vlan": 102,
    "bgpPeers": [{"asn": 64500, "bgpStatus": "up", "authKeyState": "configured"}]
  }
]
```

Direct Connect Gateway: dxgw-prod (both VIFs attached)
