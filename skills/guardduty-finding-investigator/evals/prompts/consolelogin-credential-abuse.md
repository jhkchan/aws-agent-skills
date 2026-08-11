# Eval prompt: consolelogin-credential-abuse

Diagnose the GuardDuty finding below. Walk the finding-type-driven
diagnostic tree and emit the standard diagnostic block (FINDING, VERDICT,
REASON, LAYER, SEVERITY, EVIDENCE, SUPPRESSION, REMEDIATION). The FINDING
line must reference the test-case id `consolelogin-credential-abuse`.

Symptom: GuardDuty finding i9j0k1l2 in detector 12ab34cd (us-east-1).
Type `UnauthorizedAccess:IAMUser/ConsoleLogin`, severity 7.0 (High).

```text
aws guardduty get-findings:
  service.action.awsApiCallAction.api: "ConsoleLogin"
  service.action.awsApiCallAction.remoteIpDetails.ipAddressV4:
    "203.0.113.99"
  service.action.awsApiCallAction.remoteIpDetails.location.country:
    "Country X"
  resource.accessKeyDetails.principalId: "AIDACKCEVSQALICE"
  service.additionalInfo.loginMeta.notConsole: false

CloudTrail lookup-events (ConsoleLogin in finding window):
  sourceIPAddress: 203.0.113.99
  userIdentity.arn: arn:aws:iam::111111111111:user/alice
  userIdentity.type: IAMUser
  additionalEventData.MFAUsed: No
  responseElements.ConsoleLogin: Success

aws iam get-credential-report (alice row):
  password_last_used: 45 days ago
  access_key_1_last_used_date: 45 days ago
  mfa_active: true (MFA registered but not used in this login)

Corporate identity provider logs:
  no SAML assertion issued for alice in the finding window
  alice's expected corporate egress CIDR: 198.18.0.0/15

aws guardduty list-ip-sets:
  (empty — 203.0.113.99 not in any trusted list)
```

Emit the standard diagnostic block.
