# Diagnostic Commands — Pinpoint Campaign Deployer

Post-deployment verification command listing. Loaded on demand by the skill.

## Verification commands (run after deployment)

```bash
# Verify campaign state
aws pinpoint get-campaign --application-id <id> --campaign-id <campaign-id> --query 'CampaignDefinition.State'
# Verify segment count
aws pinpoint get-segment-estimate --application-id <id> --segment-id <seg> --query 'SegmentSize'
# Verify email channel
aws pinpoint get-email-channel --application-id <id> --query 'EmailChannelResponse.Enabled'
# Verify journey state
aws pinpoint get-journey --application-id <id> --journey-id <jid> --query 'JourneyResponse.State'
# Verify event stream
aws pinpoint get-event-stream --application-id <id> --query 'EventStream.DestinationStreamArn'
```

