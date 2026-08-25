# Error Handling — cloudtrail-missing-events-troubleshooter

## Malformed input (INSUFFICIENT_DATA re-prompt)

If the input is malformed (missing TrailName, absent symptom, no
specific EventSource or EventName), emit `VERDICT: INSUFFICIENT_DATA`
and re-prompt for: (1) the specific event they expect to see
(EventSource and EventName, e.g., `s3.amazonaws.com:GetObject`),
(2) the TrailName, (3) the caller account (especially if it is a
member account of an organization), and (4) the approximate time
window of the expected event.
