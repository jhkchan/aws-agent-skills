# Eval prompt: segment-zero-endpoints

Design a deployment plan for a Pinpoint SMS promotional campaign. Emit
the standard VERDICT block.

Requirements:

- Project: app-abc123 (prod-engagement)
- Channel: SMS (origination number +12025550100 provisioned, spend limit
  $5000/month)
- Segment: seg-vip-android-users (demographic — DeviceType=android,
  tier=vip, lifecycle=active, region=ap-southeast-2)
- Template: vip-promo-sms (SMS template with Liquid {{UserAttributes.FirstName}})
- Schedule: IMMEDIATE

Existing-account context: the SMS channel is enabled and the origination
number +12025550100 is provisioned and active. The segment
seg-vip-android-users was created yesterday.

`aws pinpoint get-segment-estimate --application-id app-abc123
--segment-id seg-vip-android-users` returns SegmentSize: 0.

The combination of android + vip + active + ap-southeast-2 is too
restrictive — no endpoints in the project match all four dimensions
simultaneously. The operator expects the campaign to reach hundreds of
users but does not realize the segment is empty.
