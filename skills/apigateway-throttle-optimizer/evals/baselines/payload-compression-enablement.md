# Baseline (no-skill) response: payload-compression-enablement

This file captures what a generic assistant produces WITHOUT the
apigateway-throttle-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, DTO cost math, gzip ratio
projection, field filtering recommendation, CONFIRM gate).

---

Your API is returning large JSON payloads averaging 180 KB per response.
That is a lot of data transfer at 50 million requests per month — about
8.8 TB outbound. You should enable compression to reduce transfer costs.

API Gateway supports gzip compression. Set the minimumCompressionSize to
1024 bytes so responses above 1 KB get compressed:

```
aws apigateway update-rest-api \
  --rest-api-id <api-id> \
  --patch-operations op=add,path=/minimumCompressionSize,value=1024
```

Your backend Lambda also needs to return Content-Encoding: gzip for this
to work. JSON typically compresses to about 30% of the original size, so
your transfer costs should drop significantly.

You might also want to look at filtering response fields since clients
only use 30% of the returned data.
