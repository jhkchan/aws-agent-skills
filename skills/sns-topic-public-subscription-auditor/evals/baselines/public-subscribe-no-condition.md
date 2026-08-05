# Baseline (no-skill) response: public-subscribe-no-condition

This file captures what a generic assistant produces WITHOUT the
sns-topic-public-subscription-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, push-exfiltration reasoning).

---

This SNS topic policy grants sns:Subscribe and sns:Publish to Principal "*",
which means anyone can subscribe to the topic and publish messages to it.
This is a significant security risk because anyone on the internet can
register an endpoint to receive all messages, and also inject arbitrary
messages.

You should remove the wildcard principal from the policy and replace it
with specific account or role ARNs. The topic does have KMS encryption and
delivery logging configured which is good.
