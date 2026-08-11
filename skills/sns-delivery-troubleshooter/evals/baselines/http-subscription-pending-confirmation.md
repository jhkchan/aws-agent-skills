# Baseline (no-skill) response: http-subscription-pending-confirmation

---

Your SNS topic isn't delivering to the webhook. Check that the
endpoint URL is correct and reachable. Try publishing a test message
from the CLI and see if the endpoint receives it.

If the endpoint isn't getting anything, it could be a network issue
or a firewall blocking SNS. Make sure the endpoint allows inbound
HTTPS from AWS IP ranges. You might also want to check that the SNS
topic policy allows publishing.
