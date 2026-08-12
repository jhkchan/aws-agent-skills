# Eval: caa-record-conflict

**Difficulty:** hard
**Branch:** REVIEW_REQUIRED — renewal FAILED, CAA records only authorize letsencrypt.org not amazon.com, fix is to add amazon.com CAA record

## Prompt

My ACM certificate for www.example.com
(arn:aws:acm:us-east-1:123456789012:certificate/caa-conflict-001)
is 45 days from expiry but renewal status shows FAILED. The
certificate is DNS-validated and attached to an ALB. DNS
validation records are present. Check CAA records for
example.com — I recently switched my DNS provider and they may
have added CAA records. Account 123456789012, us-east-1.
