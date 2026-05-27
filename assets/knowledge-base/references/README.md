# Knowledge-base References

JSON / Markdown files that encode rules, rubrics, and reference data consumed by the harness layer (`packages/harness/`) and Wave 2 Pass 3 verifier.

## Schema convention (v0.4.0+)

JSON files in this directory follow a uniform top-level structure:

```jsonc
{
  "schema_version": "0.1.x",          // semver; bump on additive change, major on breaking
  "sources": [                        // repo-relative paths (with optional #anchor) for traceability
    "path/to/source-doc#section"
  ],
  // ... rest of schema, file-specific
}
```

**Why this convention:**
- `schema_version` enables consumer-side migration logic without breaking on rev bumps
- `sources` as path array (vs single doc-name string) is link-rot resistant — paths are git-tracked, doc names are not
- Mixing English keys + Chinese values is intentional: keys are interfaces (machine), values are domain knowledge (human-readable)

## Files

| File | Purpose | Consumed by |
|---|---|---|
| `forbidden-patterns.json` | R-2 forbidden language patterns (4 categories) | `harness/policy/rules_loader.py` (Task 6), Wave 2 Pass 3 verifier |
| `truthfulness-checklist.json` | R-1 truthfulness 护栏 + 2 anchor examples + 2 detection heuristics | `harness/policy/rules_loader.py` (Task 6), Wave 2 Pass 3 verifier |
| `recognition-rubric.md` | Recognition 评分判准 (8 industry columns × 4 levels) | Manual scoring of `experience-bank/index.json` |
| `vertical-fit-rubric.md` | Vertical fit 评分判准 (5 lens × 4 levels) | Same as above |
| `speedlearn-whitelist.json` | Speedlearn approved skills (legacy `_comment` / `_protocol` convention — predates v0.4.0 schema) | Multiple |
| `search-keywords.json` | JD search keyword aggregator (legacy convention) | Multiple |
| `blacklist.txt` | Plain-text company / domain blacklist | Pre-filter stage |

## Legacy convention vs v0.4.0+

`speedlearn-whitelist.json` and `search-keywords.json` predate the v0.4.0 Harness foundation and use a `_comment` / `_protocol` underscore-prefixed metadata convention. New JSON files in this directory should follow the v0.4.0+ convention (`schema_version` / `sources`). Migrating the legacy files is out of scope for Wave 1 — see backlog.

## Deferred per code review (2026-05-04)

- `actions_when_unsourced` flat string array in `truthfulness-checklist.json` — should eventually become objects with `when` conditions extracted from `quality-pass.md` Pass 3 prose. Schema bump to `0.2.0` when fixed.
- `pattern` regex support in `forbidden-patterns.json` — `match_type` field reserves space; add `"regex"` value when first regex rule needs encoding.
- `id` stable handles for entries — useful when verifier reports `"violated rule FP-COLLOQ-001"`. Add when reporting needs it.
- Per-entry `severity` / `scope` qualifiers — needed when Wave 2 verifier grades vs. matches. Add at `0.2.0`.

See `docs/architecture/HARNESS_COMPLIANCE_AUDIT.md` for the broader retrofit gap list.
