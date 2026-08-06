# Eval prompt: routing-gap-app-subnet-bypass

Audit the following AWS Network Firewall configuration for security exposure.
Emit the standard VERDICT block (FIREWALL, VERDICT, REASON, FINDINGS,
REMEDIATION).

Firewall name: fw-routing-gap-app-subnet-bypass
Firewall ARN: arn:aws:network-firewall:us-east-1:111111111111:firewall/fw-routing-gap-app-subnet-bypass

Firewall policy:

```json
{
  "StatelessDefaultActions": ["aws:forward_to_sfe"],
  "StatelessFragmentDefaultActions": ["aws:forward_to_sfe"],
  "StatefulDefaultActions": ["aws:drop_strict"],
  "TLSInspectionConfigurationArn": "arn:aws:network-firewall:us-east-1:111111111111:tls-inspection-config/tls-prod",
  "StatefulRuleGroupReferences": [
    {
      "ResourceArn": "arn:aws:network-firewall:us-east-1:111111111111:stateful-rulegroup/block-c2",
      "Priority": 1
    }
  ],
  "StatelessRuleGroupReferences": []
}
```

Stateful rule group "block-c2" (STRICT_ORDER):

```json
{
  "RulesSource": {
    "RulesString": "drop ip any any -> [198.51.100.0/24, 203.0.113.0/24] any\n"
  }
}
```

Route table for app-subnet (rtb-bbb):

```
10.0.0.0/16  -> local
0.0.0.0/0    -> igw-0abc123def456  (INTERNET GATEWAY — direct, bypasses firewall)
```

Route table for fw-subnet (rtb-ccc):

```
10.0.0.0/16  -> local
0.0.0.0/0    -> igw-0abc123def456
```

Logging configuration:

```
AlertLogs: enabled (CloudWatchLogs fw-alerts)
FlowLogs: enabled (CloudWatchLogs fw-flow)
```
