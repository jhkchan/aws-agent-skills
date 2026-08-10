# Eval prompt: insufficient-context-need-trail-name

Diagnose the following CloudTrail gap report. Determine whether the
provided context is sufficient to walk the decision tree, or emit
NEED_MORE_INFO with the specific missing inputs.

## Scenario

A user reports that "my CloudTrail seems broken". They provide only
a verbal report.

## Known facts

- User statement: "my CloudTrail seems broken".
- No trail name provided.
- No account ID provided.
- No region provided.
- No specific expected event or event source named.
- No `describe-trails` output provided.
- No `get-trail-status` output provided.
- No `lookup-events` query attempted.
- No S3 bucket name or KMS key ARN provided.
- No mention of whether the trail is single-account or organization.

## Symptom

Vague report of CloudTrail being broken. The diagnostic walk cannot
begin without identifying the specific trail and the gap.
