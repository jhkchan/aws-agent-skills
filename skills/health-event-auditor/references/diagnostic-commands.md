# Diagnostic Commands — AWS Health Event Auditor

Remediation and pre-flight command listings, moved verbatim from SKILL.md. Load on demand.

## Remediation guidance — per-verdict commands (moved from SKILL.md)

### For UNRESOLVED_EVENT — open issue with impaired entities

1. Verify the impaired entities are still impaired:
   `aws health describe-affected-entities --filter eventArn=<arn>
   --region us-east-1 --output json`
   Page via `--next-token` until exhausted.
2. For each `IMPAIRED` entity, apply the prescribed action from the
   event description. For EC2 degraded-performance, the typical action
   is stop/start:
   `aws ec2 stop-instances --instance-ids <id> --region <resource-region>`
   wait for `Stopped`, then
   `aws ec2 start-instances --instance-ids <id> --region <resource-region>`
3. Re-fetch the entity status after remediation. The status may take
   5-15 minutes to update from `IMPAIRED` to `RESOLVED`.
4. If all entities are `RESOLVED` but `eventStatus` is still `open`,
   open a Support case referencing the eventArn and the entity
   resolutions. Do NOT leave the event open — it pollutes future audits.

### For SCHEDULED_CHANGE — upcoming scheduled change

1. Identify the deadline (`startTime`) and the prescribed action from
   the event description.
2. Schedule the action during the operator's maintenance window,
   BEFORE the deadline. For EC2 instance retirement:
   `aws ec2 stop-instances --instance-ids <id>`
   `aws ec2 start-instances --instance-ids <id>`
   (Stop/start, not reboot — reboot does not migrate hosts.)
3. For multi-entity scheduled changes, batch the actions to minimize
   availability impact (e.g., cycle through an ASG rather than stop all
   instances at once).
4. After the deadline, the event transitions to `closed`. Verify the
   post-action state:
   `aws health describe-affected-entities --filter eventArn=<arn>`

### For CONFIG_GAP — org view disabled

1. From the Organizations MANAGEMENT account (not a delegated admin):
   `aws health enable-health-service-access-for-organization
   --region us-east-1`
2. Verify activation:
   `aws health describe-health-service-status-for-organization
   --region us-east-1`
   The `healthServiceAccessStatusForOrganization` field should read
   `enabled`.
3. Optionally register a delegated administrator for ongoing audits:
   `aws organizations register-delegated-administrator
   --account-id <security-tooling-account>
   --service-principal health.amazonaws.com`
4. Re-run the org-scope audit to enumerate events across all member
   accounts. Events that were previously invisible now surface.

### For CONFIG_GAP — missing EventBridge aws.health rule

1. Create the rule on the default event bus in EACH account (or use
   org-wide stacks via CloudFormation StackSets):
   `aws events put-rule --name HealthEventRouter --event-bus-name default
   --event-pattern '{"source":["aws.health"]}' --region us-east-1`
2. Add a target (SNS topic, Lambda, or Step Functions):
   `aws events put-targets --rule HealthEventRouter --event-bus-name
   default --targets file://targets.json --region us-east-1`
3. Verify the event bus policy allows `health.amazonaws.com` to put
   events:
   `aws events describe-event-bus --name default --region us-east-1`
   If no statement authorises `events:PutEvents` from
   `health.amazonaws.com`, add it:
   `aws events put-permission --event-bus-name default
   --statement-id HealthAllow --action events:PutEvents
   --principal health.amazonaws.com`
4. Test by emitting a mock event via `aws events put-events` (for the
   default bus) or wait for the next real Health event.

### For OK

1. No remediation required for the current posture.
2. Recommend verifying Health Organizational View status quarterly
   (the field can be inadvertently disabled by org-management changes).
3. Recommend reviewing the EventBridge aws.health rule set quarterly to
   catch target drift (Lambda deprecation, SNS topic deletion).
4. For closed events with active post-state verification (e.g., a
   migrated instance), confirm the resource is healthy in its own
   service console before considering the incident fully closed.

