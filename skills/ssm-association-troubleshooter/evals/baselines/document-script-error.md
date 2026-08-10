# Baseline (no-skill) response: document-script-error

This file captures what a generic assistant produces WITHOUT the
ssm-association-troubleshooter skill loaded — note the absence of
the orchestration-vs-target status distinction, the S3 output
fetch, and the structured drill-down that the skill adds.

---

The association is reporting per-target failures with "Plugin
errors occurred". You should look at the script in the SSM
document and see if there are any bugs.

The error log mentions `jq: command not found`, so the script is
trying to use jq but it is not installed on the instance. You
should install jq on the instance or modify the document to not
use jq.
