# Example: Troubleshoot Missing CloudTrail Events

## Scenario
Management events logging correctly but S3 data events missing.

## Steps
1. Check trail status: IsLogging=true
2. Check event selectors: ManagementEvents=All
3. Check data events: AdvancedEventSelectors for S3
4. Fix: Add data event selector for S3
5. Verify: lookup-events for S3 data events
