# Eval prompt: versioning-lifecycle

Design a lifecycle policy for a versioned bucket with both current-version
and non-current-version rules. Emit the standard LIFECYCLE block.

Design reference: versioning-lifecycle
Account: 111111111111
Region: us-east-1

Bucket: versioned-data-bucket
Versioning: enabled

Requirements:
- Current versions: Standard to IA at 30 days, Glacier IR at 90 days.
- Non-current versions: transition to IA at 30 days, expire at 120 days.
- Abort incomplete multipart uploads after 7 days.
- Remove expired object delete markers.

Include both current-version and non-current-version rules in the
lifecycle configuration.
