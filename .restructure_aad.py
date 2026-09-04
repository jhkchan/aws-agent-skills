#!/usr/bin/env python3
"""Restructure amplify-app-deployer to progressive disclosure. Zero-loss, byte-identical frontmatter."""
import subprocess, sys, yaml
from collections import Counter
from pathlib import Path

ROOT = Path('<repo-root>')
SKILL = 'amplify-app-deployer'
P = ROOT / 'skills' / SKILL / 'SKILL.md'

orig = P.read_text()
lines = orig.split('\n')

# locate closing frontmatter fence (line index)
close = None
for i in range(1, len(lines)):
    if lines[i] == '---':
        close = i
        break
assert close == 23, close
fm_lines = lines[:close + 1]           # through closing '---' inclusive
body = lines[close + 1:]               # 1-indexed body line N == body[N-1]

OFF = close + 1  # file line f -> body[f - 1 - OFF]; body line 1 == file line 25

def L(f):  # file line number (as shown by Read) -> its text
    return body[f - 1 - OFF]

# sanity anchors (file numbering)
assert L(25) == '', L(25)
assert L(26) == '# Amplify App Deployer', L(26)

# ---- moves: (start, end, first_line_prefix, last_line_prefix, dest, stub_lines) ----
AP = 'advanced-patterns'; WE = 'worked-examples'; EH = 'error-handling'
BDR = 'build-and-domain-reference'; G2 = 'backend-gen2-reference'

moves = [
    # M1 Mindset behaviours 66-84
    (66, 84, '- **The buildspec (amplify.yml) is the source of truth.**', '  but skip DNS validation wait hours for a cert that never issues.', AP,
     ['Senior-engineer behaviours (buildspec as source of truth; rendering mode;',
      'DNS validation before cert issue): [references/advanced-patterns.md](references/advanced-patterns.md).']),
    # M2 Philosophy body 88-111
    (88, 111, '- **Amplify Gen 2 (TypeScript CDK) replaces', '  the next push that includes `amplify.yml`. Always commit.', AP,
     ['Provisioning philosophy (Gen 2 over Gen 1; branch environments; Secrets',
      'Manager env vars; committed headers): [references/advanced-patterns.md](references/advanced-patterns.md).']),
    # M3 gotchas 169-177
    (169, 177, '- A Next.js SSR app needs the Amplify SSR compute role', '  account.', AP,
     ['Cross-dependency gotchas (SSR compute role, third-party DNS validation,',
      'ampx IAM + CDK bootstrap): [references/advanced-patterns.md](references/advanced-patterns.md).']),
    # M10 Step 7 backend detail 418-436
    (418, 436, '**Backend resources (Gen 2 patterns):**', 'CDK bootstrap (`CDKToolkit`) must exist in the account.', G2,
     ['Gen 2 backend resource catalog (auth/data/storage/functions) + build-phase',
      'pipeline-deploy contract: [references/backend-gen2-reference.md](references/backend-gen2-reference.md).']),
    # M11 Step 5 headers yaml 349-364
    (349, 364, '```yaml', '```', BDR,
     ['Full customHeaders + redirects YAML (HSTS, CSP, 301s, SPA rewrite):',
      '[references/build-and-domain-reference.md](references/build-and-domain-reference.md).']),
    # M12 Step 6 domain bash 373-388
    (373, 388, '```bash', '```', BDR,
     ['ACM cert request + domain-association commands:',
      '[references/build-and-domain-reference.md](references/build-and-domain-reference.md).']),
    # M4 Step 9 body 471-489
    (471, 489, '- **Amplify Gen 2 TypeScript CDK backend (2024-2025):**', 'Gen 2 backends; generates `ui-components/` from Figma.', AP,
     ['Gen 2 feature detail (CDK backend, branch backends, build image, SSR',
      'roles, Secrets Manager, Studio): [references/advanced-patterns.md](references/advanced-patterns.md).']),
    # M5 Step 10 body 493-501
    (493, 501, '- **Amplify apps are public-internet by default.**', '  selection.', AP,
     ['Transit/networking edge cases (no VPC attachment, NAT for private',
      'backends, second CloudFront): [references/advanced-patterns.md](references/advanced-patterns.md).']),
    # M6 WE React SPA 589-611 (heading moves with it)
    (589, 611, '### Worked example — React SPA with S3 + CloudFront-equivalent', '```', WE,
     ['Further worked examples (React SPA static site; PREREQUISITES_MISSING with',
      'no Git provider / no amplify.yml): [references/worked-examples.md](references/worked-examples.md).']),
    # M7 WE PREREQ 613-628 (heading moves with it; shared stub above covers it)
    (613, 628, '### Worked example — PREREQUISITES_MISSING', '```', WE, None),
    # M8 Error handling table 632-640
    (632, 640, '| Error | Cause | Fix |', '| `404 on dynamic routes` | SSR deployed as SPA | Switch to SSR (auto-detected) or SSG with rewrite rule |', EH,
     ['Error-to-cause-to-fix table (repo access, ampx missing, SSR role, cert',
      'timeout, CDK bootstrap, 404s): [references/error-handling.md](references/error-handling.md).']),
    # M9 Recent AWS features 644-666
    (644, 666, '- **Amplify Gen 2 (2024-2025):** TypeScript CDK-based backend with', '  PAT-based auth for long-lived CI connections.', AP,
     ['Recent AWS features (2024-2026) — Gen 2, branch backends, Secrets',
      'Manager, Node 20, Studio, CodeConnections: [references/advanced-patterns.md](references/advanced-patterns.md).']),
]

# verify anchors, then translate file-line ranges to body indices (0-based: s-OFF .. e-OFF inclusive)
for (s, e, fp, lp, dest, stub) in moves:
    assert body[s - 1 - OFF].startswith(fp), (s, body[s - 1 - OFF][:60])
    assert body[e - 1 - OFF].strip() == lp.strip() or body[e - 1 - OFF].strip().startswith(lp.strip()), (e, body[e - 1 - OFF][:60])
moves = [(s - OFF, e - OFF, fp, lp, dest, stub) for (s, e, fp, lp, dest, stub) in moves]

# check ranges are non-overlapping and ordered
rngs = sorted((m[0], m[1]) for m in moves)
for a, b in zip(rngs, rngs[1:]):
    assert a[1] < b[0], (a, b)

# ---- build new body ----
moved_out = set()
for (s, e, *_rest) in moves:
    moved_out.update(range(s, e + 1))

new_body = []
blocks = {d: [] for d in {m[4] for m in moves}}
cur = 0
n = len(body)
while cur < n:
    if cur in moved_out:
        # find the move starting here; emit stub once at its start
        for (s, e, fp, lp, dest, stub) in moves:
            if s == cur:
                if stub:
                    new_body.extend(stub)
                blocks[dest].append(body[s:e + 1])   # verbatim slice
        # skip whole contiguous run of moved lines
        while cur < n and cur in moved_out:
            cur += 1
    else:
        new_body.append(body[cur])
        cur += 1

# ---- References section before '## Domain' ----
refs_section = [
    '## References (load on demand)',
    '',
    '- [Worked examples](references/worked-examples.md) - further checklists: React SPA static site; PREREQUISITES_MISSING (no Git provider / no amplify.yml)',
    '- [Error handling](references/error-handling.md) - error-to-cause-to-fix table: repo access, ampx missing, SSR role, cert validation, CDK bootstrap, branch-scoped env vars, 404s',
    '- [Advanced patterns](references/advanced-patterns.md) - senior-engineer behaviours, philosophy tenets, cross-dependency gotchas, Gen 2 features, networking edge cases, recent AWS features',
    '- [Build and domain reference](references/build-and-domain-reference.md) - deep buildspec + domain detail: custom headers/redirects YAML, ACM cert request + domain association commands',
    '- [Gen 2 backend reference](references/backend-gen2-reference.md) - Gen 2 backend patterns: resource catalog, pipeline-deploy build-phase contract',
]
di = next(i for i, l in enumerate(new_body) if l == '## Domain')
new_body[di:di] = refs_section + ['']

# ---- reference files ----
REFDIR = ROOT / 'skills' / SKILL / 'references'
TITLES = {
    'worked-examples': 'Worked examples',
    'error-handling': 'Error handling',
    'advanced-patterns': 'Advanced patterns',
}
new_files, extended = {}, {}
for dest, blist in blocks.items():
    if not blist:
        continue
    f = REFDIR / f'{dest}.md'
    if dest in TITLES:  # brand-new file
        assert not f.exists(), f
        hdr = [f'# {TITLES[dest]} - Amplify App Deployer', '',
               '> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.', '']
        new_files[f] = '\n'.join(hdr + ['\n'.join(b) for b in blist]) + '\n'
    else:               # extend existing file
        assert f.exists(), f
        titles_map = {
            'build-and-domain-reference': [('Moved from SKILL.md Step 5 — custom headers + redirects YAML'),
                                           ('Moved from SKILL.md Step 6 — ACM cert + domain association commands')],
            'backend-gen2-reference': [('Moved from SKILL.md Step 7 — backend resources + pipeline-deploy contract')],
        }
        parts = []
        for t, b in zip(titles_map[dest], blist):
            parts.append(f'## {t}\n\n' + '\n'.join(b))
        existing = f.read_text()
        assert existing.endswith('\n')
        extended[f] = existing + '\n' + '\n\n'.join(parts) + '\n'

# ---- verification ----
old_body_count = orig.split('---', 2)[2].count('\n')
new_content = '\n'.join(fm_lines + new_body)
new_body_nl = new_content.split('---', 2)[2].count('\n')

# frontmatter byte-identical vs git HEAD
head = subprocess.run(['git', '-C', str(ROOT), 'show', f'HEAD:skills/{SKILL}/SKILL.md'],
                      capture_output=True, text=True).stdout
assert head.split('---', 2)[1] == new_content.split('---', 2)[1], 'FRONTMATTER DRIFT vs HEAD'
assert orig.split('---', 2)[1] == new_content.split('---', 2)[1]

# zero-loss multiset
old_counter = Counter(body)
new_counter = Counter(new_body)
for c in extended.values():
    new_counter += Counter(c.split('\n'))
for c in new_files.values():
    new_counter += Counter(c.split('\n'))
lost = old_counter - new_counter
assert not lost, f'LOST LINES: {lost}'

# accounting: new body + refs >= old body
ref_line_total = sum(len(c.split('\n')) for c in list(new_files.values()) + list(extended.values()))
accounting_ok = len(new_body) + ref_line_total >= len(body)

# YAML parses; description untouched
parts = new_content.split('---', 2)
yaml.safe_load(parts[1])
desc_ok = len(parts[1].split('description:')[1]) > 0

moved_bytes = sum(len('\n'.join(body[m[0]:m[1] + 1])) for m in moves)

report = {
    'skill': SKILL,
    'old_body_nl': old_body_count, 'new_body_nl': new_body_nl,
    'old_body_lines': len(body), 'new_body_lines': len(new_body),
    'moved_blocks': len(moves), 'moved_bytes': moved_bytes,
    'new_files': sorted(str(f.name) for f in new_files),
    'extended_files': sorted(str(f.name) for f in extended),
    'zero_loss': 'PASS (multiset empty)', 'frontmatter': 'BYTE-IDENTICAL vs HEAD',
    'accounting_new_plus_refs_ge_old': accounting_ok,
    'yaml': 'OK', 'under_500': new_body_nl < 500,
}
import json; print(json.dumps(report, indent=1))

if '--write' in sys.argv:
    P.write_text(new_content)
    for f, c in new_files.items():
        f.write_text(c)
    for f, c in extended.items():
        f.write_text(c)
    print('WROTE files.')
else:
    print('DRY RUN — pass --write to apply')
