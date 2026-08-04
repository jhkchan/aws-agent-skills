# Eval prompt: single-connection-no-redundancy

Audit the following Direct Connect topology for resilience and security
posture. Emit the standard VERDICT block (CONNECTION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Direct Connect topology for account 111111111111 (region us-east-1):

Connections (aws directconnect describe-connections):

```json
[
  {
    "connectionId": "dxcon-single-connection-no-redundancy",
    "connectionName": "dc-to-hq",
    "connectionState": "available",
    "bandwidth": "1Gbps",
    "location": "EqSE2",
    "region": "us-east-1",
    "lagId": null,
    "connectionMode": "standard",
    "macSecCapable": false,
    "encryptionMode": "no_encrypt",
    "hasLogicalRedundancy": "no"
  }
]
```

Virtual interfaces (aws directconnect describe-virtual-interfaces):

```json
[
  {
    "virtualInterfaceId": "dxvif-private-prod",
    "virtualInterfaceType": "private",
    "connectionId": "dxcon-single-connection-no-redundancy",
    "vlan": 101,
    "bgpPeers": [
      {"asn": 64512, "bgpStatus": "down", "authKey": null}
    ]
  }
]
```

Direct Connect Gateways: none
