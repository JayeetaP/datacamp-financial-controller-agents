---
name: code-change-verification
description: Verify changes to code, tests, evals, schemas, data, or build behavior in this repository before handoff.
---

# Code-change verification

Run the narrowest relevant check first, then the repository gate:

```bash
uv run pytest <target>
make verify
```

Also verify the observable artifact affected by the change: data-quality report, finding JSON,
draft adjustment, run record, or close package. Confirm that no real data, credentials, generated
run artifacts, or authentication caches entered Git.

Report commands run, results, remaining live-only checks, and any intentional demo failure. Do not
claim live Codex behavior was tested when only replay mode ran.
