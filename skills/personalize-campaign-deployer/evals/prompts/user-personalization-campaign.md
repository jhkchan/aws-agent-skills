# Eval: user-personalization-campaign

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CUSTOM dataset group, aws-user-personalization recipe, HPO training, campaign minProvisionedTPS=1, event tracker enabled

## Prompt

Build a Personalize recommendation system for a retail site in
us-east-1. CUSTOM dataset group named retail-recs. Interactions data
at s3://training-data/interactions.csv (USER_ID, ITEM_ID, TIMESTAMP,
EVENT_TYPE). Use the User-Personalization recipe with HPO. Campaign
minProvisionedTPS=1 (dev). Enable an event tracker for real-time
updates. Role arn:aws:iam::123456789012:role/PersonalizeServiceRole.
Account 123456789012.
