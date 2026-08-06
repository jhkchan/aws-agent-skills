# Eval prompt: permissive-fragment-default-pass

Audit the following AWS Network Firewall configuration for security exposure.
Emit the standard VERDICT block (FIREWALL, VERDICT, REASON, FINDINGS,
REMEDIATION).

Firewall name: fw-permissive-fragment-default-pass
Firewall ARN: arn:aws:network-firewall:us-east-1:111111111111:firewall/fw-permissive-fragment-default-pass

Firewall policy:

```json
{
  "StatelessDefaultActions": ["aws:forward_to_sfe"],
  "StatelessFragmentDefaultActions": ["aws:pass"],
  "StatefulDefaultActions": ["aws:drop_strict"],
  "TLSInspectionConfigurationArn": "arn:aws:network-firewall:us-east-1:111111111111:tls-inspection-config/tls-prod",
  "StatefulRuleGroupReferences": [
    {
      "ResourceArn": "arn:aws:network-firewall:us-east-1:111111111111:stateful-rulegroup/scoped-blocks",
      "Priority": 1
    }
  ],
  "StatelessRuleGroupReferences": []
}
```

Stateful rule group "scoped-blocks" (STRICT_ORDER):

```json
{
  "RulesSource": {
    "RulesString": "drop ip any any -> [198.51.100.0/24, 203.0.113.0/24] any\n"
  }
}
```

Route table for app-subnet (rtb-fff):

```
10.0.0.0/16  -> local
0.0.0.0/0    -> eni-firewall-az1  (firewall ENI in AZ1)
```

Logging configuration:

```
AlertLogs: enabled (CloudWatchLogs fw-alerts)
FlowLogs: enabled (CloudWatchLogs fw-flow)
```
