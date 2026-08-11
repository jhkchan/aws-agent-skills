# Baseline (no-skill) response: distribution-in-progress-missing

This file captures what a generic assistant produces WITHOUT the
cloudfront-response-headers-deployer skill loaded — the contrast that
proves the skill catches the InProgress distribution state before
attempting an update that would fail with PreconditionFailed.

---

To attach the managed SecurityHeadersPolicy to distribution
E27TVSIEXAMPLE:

1. Go to CloudFront → Distributions → select E27TVSIEXAMPLE.
2. Edit the distribution.
3. Under the default cache behavior, set Response Headers Policy to
   "SecurityHeadersPolicy".
4. Save changes.

That's it. The policy will be attached once the distribution finishes
updating.

Let me know if you have any questions.
