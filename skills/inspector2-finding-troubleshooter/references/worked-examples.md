# Worked Examples — Inspector v2 Finding Diagnoses

Full walkthroughs beyond the primary example in SKILL.md (Critical
package CVE on EC2). Each block follows the strict output contract:
TARGET, VERDICT, REASON, FINDING_TYPE, SEVERITY, LAYER, EVIDENCE,
REMEDIATION, CONFIRM.

### Worked example — Lambda code vulnerability (hardcoded secret)

```text
TARGET: arn:aws:lambda:us-east-1:111:function:checkout-handler
VERDICT: ROOT_CAUSE_FOUND
REASON: Function checkout-handler has a hardcoded AWS access key in
  handler.js line 42 (rule JS-HARDCODED-SECRET); CodeSnippet pinpointed
  the line (text REDACTED).
FINDING_TYPE: CODE_VULNERABILITY
SEVERITY: HIGH
LAYER: LAMBDA_SOURCE_DEFECT
EVIDENCE:
  - Finding: CODE_VULNERABILITY, rule JS-HARDCODED-SECRET, severity HIGH.
  - Probe: batch-get-code-snippets returns filePath: handler.js,
    lineNumber: 42, text: REDACTED (secret redacted; location is signal).
  - Passing: runtime nodejs20.x current; no package CVE on layers.
REMEDIATION:
  1. Remove the hardcoded key from handler.js line 42. Load the
     credential from Secrets Manager or an environment variable.
  2. Rotate the exposed key — revoke in IAM and issue a new one.
  3. Redeploy: update-function-code --function-name checkout-handler
     --zip-file fileb://deploy.zip
  4. Verify: re-scan after redeploy; the finding closes when the
     secret is no longer in the source.
CONFIRM: Before redeploying, emit and await:
  "CONFIRM: About to update-function-code on checkout-handler
   (remove hardcoded secret). Proceed? (yes/no)"
```

### Worked example — Network reachability (SG overly permissive)

```text
TARGET: arn:aws:ec2:us-east-1:111:instance/i-db99
VERDICT: ROOT_CAUSE_FOUND
REASON: Instance i-db99 has SG sg-db1 with inbound rule 0.0.0.0/0 on
  tcp/3306 (MySQL); Inspector flagged port 3306 reachable from INTERNET.
FINDING_TYPE: NETWORK_REACHABILITY
SEVERITY: CRITICAL
LAYER: SG_OVERLY_PERMISSIVE
EVIDENCE:
  - Finding: port 3306, CIDR 0.0.0.0/0, scope INTERNET, lastObservedAt
    2026-08-09T22:00Z.
  - Probe: describe-security-groups --group-ids sg-db1 returns
    IpPermissions: [{FromPort: 3306, IpRanges: [{CidrIp: 0.0.0.0/0}]}].
  - Passing: no package CVEs; no recent config change.
REMEDIATION:
  1. Revoke the 0.0.0.0/0 inbound rule on tcp/3306 (see references).
  2. Add a scoped rule: authorize-security-group-ingress --group-id
     sg-db1 --protocol tcp --port 3306 --source-security-group-id sg-app
  3. Remove the public IP if the instance does not need it.
  4. Verify: the finding closes on the next Inspector rescan.
CONFIRM: Before revoking SG ingress, emit and await:
  "CONFIRM: About to revoke-security-group-ingress on sg-db1
   (tcp/3306 from 0.0.0.0/0). Proceed? (yes/no)"
```
