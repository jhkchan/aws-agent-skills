# Eval prompt: intelligent-tiering-optin

Design an Intelligent-Tiering opt-in lifecycle policy for a bucket with
unpredictable access patterns. Emit the standard LIFECYCLE block.

Design reference: intelligent-tiering-optin
Account: 111111111111
Region: us-east-1

Bucket: data-lake-raw
Versioning: enabled
Access pattern: unpredictable (mixed frequent and infrequent access).
Requirement: enable Intelligent-Tiering for all objects with no
transition-day minimums.
Archive tier configuration: ARCHIVE_ACCESS at 90 days,
DEEP_ARCHIVE_ACCESS at 180 days.

Include both the lifecycle rule for Intelligent-Tiering opt-in and the
Intelligent-Tiering archive configuration CLI.
