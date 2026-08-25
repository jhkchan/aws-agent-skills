# Diagnostic Commands — GuardDuty Finding Severity Triage

Pre-flight safety-check and per-verdict remediation command listings, moved verbatim from SKILL.md. Load on demand.

## Pre-flight safety checks — command detail (moved from SKILL.md)

- **Capture forensic state before containment.** For CRITICAL findings:
  - EBS snapshot: `aws ec2 create-snapshot --volume-id <vol-id>
    --description "GD-forensic-<finding-id>" --tag-specifications
    'ResourceType=snapshot,Tags=[{Key=Incident,Value=<id>}]'`
  - Security-group quarantine: create a quarantine SG with no inbound
    rules, then `aws ec2 modify-instance-attribute --instance-id <id>
    --groups <quarantine-sg-id>`. This preserves the instance for
    forensics while cutting network access.

- **Understand the credential blast radius before revoking.** For
  credential-exfiltration findings, do not just list attached policies —
  simulate the principal's effective permissions to account for trust
  policies, permission boundaries, and SCPs that listing misses:
  ```bash
  aws iam simulate-principal-policy --policy-source-arn <role-arn> \
    --action-names s3:GetObject,iam:CreateUser,iam:AttachRolePolicy,sts:AssumeRole \
    --resource-arns '*' --output json --query 'EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}'
  ```
  This reveals whether the stolen credentials can create users, assume
  cross-account roles, or read S3 objects — critical for determining
  whether the attacker lateral-moved beyond the source account. Also
  check for cross-account trust policies:
  `aws iam get-role --role-name <name> --query 'Role.AssumeRolePolicyDocument'`
  — a role trusted by another account's principal means the stolen
  credentials work cross-account. Revoking credentials may break
  production workloads — have a replacement role ready.

- **Correlate with VPC Flow Logs for exfiltration confirmation.** For
  `Exfiltration:EC2/*` findings, confirm actual data movement by
  querying VPC Flow Logs for large outbound transfers to the
  exfiltration destination:
  ```bash
  aws logs start-query --log-group-name <vpc-flow-log-group> \
    --start-time <finding-eventFirstSeen-epoch> \
    --end-time <finding-eventLastSeen-epoch> \
    --query-string 'fields @timestamp, srcAddr, dstAddr, bytes, dstPort
      | filter srcAddr = "<instance-private-ip>" and isIpv4(dstAddr)
      | stats sum(bytes) as totalOut by dstAddr, dstPort
      | sort totalOut desc | limit 20'
  ```
  Look for: single-destination transfers exceeding 100 MB (sustained
  bulk exfiltration), connections to non-standard high ports (data
  exfiltration often uses 4444, 8443, 9999), and connections to known
  file-sharing endpoints (mega.co.nz, gofile.io, transfer.sh). If total
  outbound bytes to the flagged destination are under 1 MB, the
  exfiltration may be a probe, not a confirmed breach — adjust the
  REASON accordingly.

- **Prefer isolation over termination.** Isolation (security-group
  quarantine) is reversible; termination is not. A quarantined instance
  can be forensically examined; a terminated instance cannot. The ONLY
  case where immediate termination is justified is when the instance is
  actively causing harm (e.g., participating in a large DDoS attack) and
  isolation cannot stop the outbound traffic fast enough.

- **For suppression-filter creation (recurring FP):** verify the filter
  scope. `aws guardduty create-filter` with a too-broad criterion
  (e.g., filtering all `Recon:EC2/*` findings) hides genuine threats.
  Scope to the specific source IP, finding type, and resource ARN.

## Remediation guidance — per-verdict commands (moved from SKILL.md)

### For CRITICAL findings (immediate IR)

1. **Isolate the affected resource.** For EC2: create and attach a
   quarantine security group with no inbound rules:
   ```bash
   QSG=$(aws ec2 create-security-group --group-name gd-quarantine-$(date +%s) \
     --description "GuardDuty quarantine — no inbound" --vpc-id <vpc-id> \
     --query GroupId --output text)
   aws ec2 modify-instance-attribute --instance-id <id> --groups $QSG
   ```
   For IAM: attach an inline Deny-all policy to the role/user (do not
   delete — preserve for investigation):
   ```bash
   aws iam put-role-policy --role-name <name> --policy-name DenyAll \
     --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*"}]}'
   ```
2. **Revoke compromised credentials.** For instance-credential
   exfiltration: delete the stolen access keys and rotate the instance
   profile:
   ```bash
   aws iam delete-access-key --access-key-id <AKIA...> --user-name <role-session>
   aws iam list-access-keys --user-name <name>  # verify remaining keys
   ```
   For IAM-user compromise: deactivate all access keys and reset the
   password via the IAM console or `aws iam update-login-profile`.
3. **Capture forensic state.** EBS snapshot before any further changes:
   ```bash
   aws ec2 create-snapshot --volume-id <vol-id> \
     --description "GD-forensic-<finding-id>" \
     --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Incident,Value=<id>}]'
   ```
   If SSM Agent is running on the instance, capture a memory forensic
   artifact via SSM Run Command before isolation (use the
   `AWS-ConfigureAWSPackage` document to install forensic tooling).
4. **Trace lateral movement.** Query CloudTrail for all API calls made
   by the compromised principal in the 24h before and after the finding:
   ```bash
   aws cloudtrail lookup-events --lookup-attributes \
     AttributeKey=Username,AttributeValue=<principal> \
     --start-time $(date -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date +%Y-%m-%dT%H:%M:%S)
   ```
   Look for `AssumeRole`, `GetObject`, `GetSecretValue`, and any
   infrastructure-modification calls.
5. **Notify the IR team.** CRITICAL findings should trigger the
   incident-response runbook. If the account has Security Hub enabled,
   the finding is already forwarded — verify the integration and check
   that the EventBridge rule for CRITICAL finding types routes to the
   IR pipeline (see "Security Hub integration" above).

### For HIGH findings (investigate within 4 hours)

1. **Verify the threat.** Check CloudTrail for the API call that triggered
   the finding. Confirm the source IP, the API action, and whether the
   action succeeded.
2. **Check for session validity.** For IAM findings, check whether the
   caller's session is still active (CloudTrail `userIdentity.sessionContext`).
3. **Rotate credentials if compromise is suspected.** For
   `MaliciousIPCaller` findings, rotate the access keys even if you
   cannot confirm compromise — the cost of rotation is low; the cost of
   a compromised key is high.
4. **Review security-group exposure.** For brute-force findings, check
   whether the security group restricts the targeted port to known CIDRs.
   If SSH/RDP is open to 0.0.0.0/0, tighten immediately.

### For MEDIUM findings (investigate within 24 hours)

1. **Contextualize the behavior.** Check whether the user/resource owner
   recognizes the activity (travel for console-login findings, scheduled
   job for API anomalies).
2. **Review the finding's `service.additionalInfo`.** This field often
   contains API call details, network-connection metadata, or DNS
   query specifics that help distinguish benign from malicious.
3. **Check for correlated findings.** A MEDIUM finding may be part of a
   kill-chain: Recon → Initial Access → Privilege Escalation. If a
   MEDIUM Recon finding precedes a HIGH UnauthorizedAccess finding on the
   same resource, escalate the pair.

### For LOW findings (monitor)

1. **Add to the monitoring queue.** No immediate action needed.
2. **Review exposed ports.** For PortProbeUnprotectedPort findings,
   verify the probed port should be open in the security group.
3. **Watch for escalation.** If the same source IP appears in a HIGH
   finding later, the LOW findings were reconnaissance for the attack.

### For LIKELY_FALSE_POSITIVE findings (archive)

1. **Archive the finding.** `aws guardduty archive-findings --detector-id
   <id> --finding-ids <fid>`.
2. **Create a suppression filter for recurring FPs.** If the same FP
   pattern recurs (same scanner IP, same DNS domain), create a filter:
   `aws guardduty create-filter --name suppress-nessus-scan
   --action '{"name": "ARCHIVE"}' --finding-criteria <json>`.
3. **Document the FP rationale.** Record WHY the finding was classified
   as FP (which pattern matched, what evidence supported it). This helps
   future analysts understand the suppression and prevents re-opening
   the finding.
4. **Periodically review suppression filters.** FP patterns change —
   a scanner IP that was authorized may become compromised. Review
   suppression filters quarterly.

