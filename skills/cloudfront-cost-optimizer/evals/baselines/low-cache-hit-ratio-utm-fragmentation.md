# Baseline (no-skill) response: low-cache-hit-ratio-utm-fragmentation

---

Your cache hit ratio is only 58% which is low for static content.
You should look at your cache policy. The UTMs in the query string
whitelist are probably causing cache fragmentation.

Try changing the cache policy to not include UTMs and see if the
hit rate improves.
