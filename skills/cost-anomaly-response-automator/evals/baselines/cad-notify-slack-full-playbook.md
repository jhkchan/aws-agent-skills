# Baseline (no-skill) response: cad-notify-slack-full-playbook

This file captures what a generic assistant produces WITHOUT the
cost-anomaly-response-automator skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, guardrails
audit, audit checklist, specific remediation with CLI).

---

Here's how you can build a cost anomaly to Slack workflow:

1. Set up a CAD monitor in the AWS Console under Cost Anomaly Detection.
2. Create an SNS topic and subscribe a Lambda that posts to your Slack
   webhook.
3. Add a budget action if you want to stop instances.

Your workflow looks good. Just deploy it with CloudFormation.
