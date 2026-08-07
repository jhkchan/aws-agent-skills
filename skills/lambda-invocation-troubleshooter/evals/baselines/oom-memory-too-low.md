# Baseline (no-skill) response: oom-memory-too-low

---

Your Lambda is running out of memory. The fix is to raise the memory
size — try 512 MB or 1 GB. Lambda memory ranges from 128 MB to 10 GB,
so you have plenty of headroom.

If the OOM persists after raising memory, you may have a memory leak
in your Node.js code. Look for module-level caches or growing arrays
that aren't being cleared.
