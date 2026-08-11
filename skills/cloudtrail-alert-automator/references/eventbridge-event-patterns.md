# EventBridge Event Patterns for CloudTrail Alerts

Supplementary reference for the CloudTrail Alert Automator skill. Use
when constructing EventBridge event patterns for CloudTrail API calls,
debugging a rule that never fires, or selecting the right filter
combination for a security alert.

## Event structure (CloudTrail via EventBridge)

Every CloudTrail management event arrives on the default EventBridge
bus with this envelope:

```json
{
  "version": "0",
  "id": "event-uuid",
  "detail-type": "AWS API Call via CloudTrail",
  "source": "aws.<service>",
  "account": "<recipient-account-id>",
  "time": "2026-08-05T12:00:00Z",
  "region": "us-east-1",
  "resources": [],
  "detail": {
    "eventVersion": "1.08",
    "userIdentity": { "type": "Root|AssumedRole|User", "arn": "...", "userName": "..." },
    "eventTime": "2026-08-05T11:55:00Z",
    "eventName": "AttachRolePolicy",
    "awsRegion": "us-east-1",
    "sourceIPAddress": "1.2.3.4",
    "userAgent": "console.amazonaws.com",
    "requestParameters": { ... },
    "responseElements": { ... },
    "readOnly": false,
    "eventType": "AwsApiCall",
    "apiVersion": "2010-05-08",
    "managementEvent": true,
    "recipientAccountId": "<source-account-id>",
    "eventCategory": "Management"
  }
}
```

## Pattern matching rules

| Filter field | CloudTrail detail field | Match type | Notes |
|---|---|---|---|
| `detail.eventName` | `eventName` | Exact, case-sensitive | List all variants explicitly |
| `detail.userIdentity.type` | `userIdentity.type` | Exact | `Root`, `AssumedRole`, `User` |
| `detail.userIdentity.arn` | `userIdentity.arn` | Exact or prefix | Full ARN for precision |
| `detail.sourceIPAddress` | `sourceIPAddress` | Exact | For CIDR matching, use Lambda post-filter |
| `detail.readOnly` | `readOnly` | Boolean | `false` = write events only |
| `detail.responseElements.ConsoleLogin` | `responseElements.ConsoleLogin` | Exact | `Success` or `Failure` |
| `detail.recipientAccountId` | `recipientAccountId` | Exact | Source account in org trail |
| `detail.eventSource` | `eventSource` | Exact | e.g., `iam.amazonaws.com` |
| `detail.awsRegion` | `awsRegion` | Exact | Per-region filtering |

## Verified patterns for common alerts

### Root console login (Success only)

```json
{
  "source": ["aws.signin"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "userIdentity": {"type": ["Root"]},
    "eventName": ["ConsoleLogin"],
    "responseElements": {"ConsoleLogin": ["Success"]}
  }
}
```

### IAM policy or credential changes (write only)

```json
{
  "source": ["aws.iam"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": [
      "AttachRolePolicy", "DetachRolePolicy", "PutRolePolicy",
      "DeleteRolePolicy", "CreatePolicyVersion", "DeletePolicy",
      "UpdateAssumeRolePolicy", "CreateAccessKey", "DeleteAccessKey",
      "UpdateAccountPasswordPolicy", "DeactivateMFADevice",
      "DeleteVirtualMFADevice"
    ],
    "readOnly": [false]
  }
}
```

### Security group open to 0.0.0.0/0 (post-filter in Lambda)

EventBridge pattern (broad SG match, Lambda narrows to 0.0.0.0/0):

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["AuthorizeSecurityGroupIngress", "AuthorizeSecurityGroupEgress"],
    "readOnly": [false]
  }
}
```

Lambda post-filter checks `requestParameters.ipPermissions` for
`cidrIp: "0.0.0.0/0"`.

### CloudTrail tampering (never suppress)

```json
{
  "source": ["aws.cloudtrail"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["DeleteTrail", "StopLogging", "UpdateTrail",
                   "DeleteEventDataStore", "PutEventSelectors"]
  }
}
```

### Multi-account IAM changes (Organizations trail)

```json
{
  "source": ["aws.iam"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["AttachRolePolicy", "CreateAccessKey"],
    "recipientAccountId": ["111111111111", "222222222222", "333333333333"]
  }
}
```

### Console login from non-corporate IP (post-filter)

EventBridge pattern matches all ConsoleLogin Success; Lambda checks
`sourceIPAddress` against a corporate CIDR allowlist parameter.

```json
{
  "source": ["aws.signin"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["ConsoleLogin"],
    "responseElements": {"ConsoleLogin": ["Success"]},
    "userIdentity": {"type": ["User", "AssumedRole"]}
  }
}
```

## Debugging a rule that never fires

1. **Verify CloudTrail is logging:** `aws cloudtrail get-trail-status
   --name <trail>` — `IsLogging` must be `true`.
2. **Test the pattern:** `aws events test-event-pattern --event-pattern
   '<pattern>' --event '<sample-event-json>'` — returns `Result: true`
   if the pattern matches.
3. **Check the rule state:** `aws events describe-rule --name <rule>`
   — `State` must be `ENABLED`.
4. **Check the bus:** CloudTrail events arrive on the `default` bus.
   A rule on a custom bus will never see CloudTrail events unless
   explicitly forwarded.
5. **Verify the event is a management event:** Data events (S3
   object-level) require `AdvancedEventSelectors` on the trail. Check
   with `aws cloudtrail get-event-selectors --trail-name <trail>`.

## lookup-events reference

| Parameter | Required | Description |
|---|---|---|
| `LookupAttributes` | Yes (at least 1) | Filter by `EventId`, `EventName`, `ReadOnly`, `Username`, `ResourceType`, `ResourceName`, `EventSource` |
| `StartTime` | No | Earliest event time (max 15 min before `EndTime`) |
| `EndTime` | No | Latest event time (default: now) |
| `MaxResults` | No | 1–50 (default 10) |

**Limitations:**
- Only management events are returned (no data events).
- 15-minute lookback ceiling per call.
- Rate limited to 1 RPS per account (burst 2, then 1/s sustained).
- Does not include CloudTrail Insights events — use `get-insight-results` for those.
