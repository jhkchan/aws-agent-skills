# Eval: missing-interactions-schema

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — operator provided Users dataset but no Interactions dataset; Interactions is the REQUIRED minimum

## Prompt

Build a Personalize recommendation system in us-east-1. CUSTOM
dataset group named retail-recs. I have a Users dataset at
s3://training-data/users.csv (USER_ID, AGE, GENDER) but no
Interactions data yet. Use User-Personalization with HPO. Campaign
minProvisionedTPS=1.
