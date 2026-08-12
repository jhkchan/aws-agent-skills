# Baseline (no-skill) response: circuit-breaker-fielddata

---

You're hitting a circuit breaker in OpenSearch. The fielddata
breaker is tripping on the request_body field. You should increase
the fielddata circuit breaker limit, or avoid aggregating on that
field.

The parent breaker hasn't tripped so it's specifically the fielddata
cache that's too large. You can disable fielddata on text fields to
fix this.
