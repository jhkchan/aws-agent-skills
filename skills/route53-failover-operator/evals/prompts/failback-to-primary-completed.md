# Eval prompt: failback-to-primary-completed

Plan the following Route 53 failback operation and emit the standard
VERDICT block (post-verification form).

Operation: failback
FQDN: api.example.com
Hosted zone: Z2ABCDEFGHIJK

```json
{
  "CurrentStateAfterPriorFailover": {
    "PRIMARY": "10.0.1.10 (was secondary, became primary during emergency)",
    "SECONDARY": "10.0.0.10 (was primary, became secondary)",
    "TTL": 60
  },
  "HealthCheckStatus": {
    "h-primary (10.0.1.10)": "Healthy (last 5 minutes)",
    "h-restored (newly created for 10.0.0.10)": "Healthy (2 consecutive intervals)"
  },
  "IndependentProbe": {
    "10.0.0.10:443 TCP": "OK",
    "10.0.0.10 /health HTTPS": "200 OK"
  },
  "PostExecutionVerification": {
    "ChangeInfo.Status": "INSYNC",
    "test-dns-answer_1.1.1.1": "10.0.0.10",
    "test-dns-answer_8.8.8.8": "10.0.0.10",
    "test-dns-answer_9.9.9.9": "10.0.0.10",
    "dig_1.1.1.1": "10.0.0.10",
    "ApplicationMetrics_120s_sample": "no error spike"
  }
}
```
