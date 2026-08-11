# Baseline (no-skill) response: case-sensitivity-mismatch

This file captures what a generic assistant produces WITHOUT the
tag-compliance-automator skill loaded.

---

The instances are showing NON_COMPLIANT even though the Lambda is
firing. This could be a timing issue — the Config rule might be
evaluating before the Lambda finishes tagging.

You could try adding a delay or checking the Config rule's
MaximumExecutionFrequency. Also verify that the Lambda is actually
successful by checking its CloudWatch logs.

Another possibility is that the tag key name in the Lambda doesn't
match what Config expects. Double-check the spelling.
