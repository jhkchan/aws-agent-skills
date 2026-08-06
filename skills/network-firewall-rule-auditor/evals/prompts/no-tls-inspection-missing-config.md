# Eval prompt: no-tls-inspection-missing-config

Audit the following AWS Network Firewall configuration for security exposure.
Emit the standard VERDICT block (FIREWALL, VERDICT, REASON, FINDINGS,
REMEDIATION).

Firewall name: fw-no-tls-inspection-missing-config
Firewall ARN: arn:aws:network-firewall:us-east-1:111111111111:firewall/fw-no-tls-inspection-missing-config

Firewall policy:

```json
{
  "StatelessDefaultActions": ["aws:forward_to_sfe"],
  "StatelessFragmentDefaultActions": ["aws:forward_to_sfe"],
  "StatefulDefaultActions": ["aws:drop_strict"],
  "TLSInspectionConfigurationArn": null,
  "StatefulRuleGroupReferences": [
    {
      "ResourceArn": "arn:aws:network-firewall:us-east-1:111111111111:stateful-rulegroup/payload-signatures",
      "Priority": 1
    }
  ],
  "StatelessRuleGroupReferences": []
}
```

Stateful rule group "payload-signatures" (STRICT_ORDER):

```json
{
  "RulesSource": {
    "RulesString": "drop http any any -> any $HTTP_PORTS (msg:\"known malware beacon\"; content:\"/c2/checkin\"; nocase; sid:1001; rev:1;)\ndrop http any any -> any $HTTP_PORTS (msg:\"suspicious user-agent\"; content:\"BadAgent\"; http_header; sid:1002; rev:1;)\n"
  }
}
```

Route table for app-subnet (rtb-ddd):

```
10.0.0.0/16  -> local
0.0.0.0/0    -> eni-firewall-az1  (firewall ENI in AZ1)
```

Logging configuration:

```
AlertLogs: enabled (CloudWatchLogs fw-alerts)
FlowLogs: enabled (CloudWatchLogs fw-flow)
```
