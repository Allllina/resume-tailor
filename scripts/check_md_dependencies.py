#!/usr/bin/env python3
"""
Methodology cross-reference / dependency analyzer for the Resume_Optimizer repo.

Scans all first-party .md files (excludes vendored / 3rd-party / root archive),
extracts inter-file references, and reports:
- short circular references (SCC ≤5; large SCCs are healthy doc cross-link webs)
- dead references (file or section doesn't exist)
- orphan files (zero inbound refs)
- fan-out (most-referenced files)

Run: python3 scripts/check_md_dependencies.py
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent

# Exclusion: precise path-prefix matching (relative to repo root)
EXCLUDE_PATH_PREFIXES = [
    "ops/jobops/",          # vendored fork (3rd party)
    "agent-browser/",       # 3rd party skill data
    "archive/",             # root-level archive of old custom resumes (NOT docs/archive)
    "node_modules/",
    "ui/node_modules/",
    "packages/harness/.venv/",
    "packages/harness/data/users/",
    "ui/test-resume.md",            # local/manual upload fixture
    ".git/",
    ".claude/",
]

# Reference pattern: catches `foo.md`, foo/bar.md, foo.md §Section
# Section captures up to whitespace or Chinese / English punctuation
REF_PATTERN = re.compile(
    r"`?([\w\-./]+\.md)`?(?:\s*§\s*([^\s,；。、`)\]<>\"'""''《》()（）]+))?"
)

SECTION_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)

# Long-SCC threshold: SCCs with more nodes than this are documentation cross-link
# webs (healthy), not real circular dependency bugs. Only short cycles get reported.
SHORT_CYCLE_MAX_NODES = 5

# Allowed orphan files (intentional, won't trigger HEALTH warning)
# Format: relative_path -> reason
ALLOWED_ORPHANS = {
    "assets/knowledge-base/references/market-contexts/hong-kong.md":
        "stub by design — promote to Full when first HK role is targeted",
    "assets/knowledge-base/references/company-contexts/automotive.md":
        "company-context overlay loaded by market/company routing; no direct doc ref required",
    "assets/knowledge-base/references/company-contexts/internet.md":
        "company-context overlay loaded by market/company routing; no direct doc ref required",
    "assets/profile/user-profile.sample.md":
        "sample seed file intentionally referenced by scripts and docs outside markdown dependency graph",
    "docs/TESTING.md":
        "testing handbook entry point; referenced by AGENTS/cold-start, not required inbound",
    "ui/AGENTS.md":
        "subproject assistant entry point for the UI workspace",
    "docs/archive/FRAMEWORK_DECISION.md":
        "v0.2.0 planning archive — kept for historical reference",
    "docs/archive/REPO_CONSOLIDATION_PLAN.md":
        "v0.2.0 planning archive — kept for historical reference",
    "docs/archive/IMPLEMENTATION.md":
        "v0.2.0 planning archive — kept for historical reference",
    "docs/archive/JOB_OPS_CUSTOMIZATION_PLAN.md":
        "v0.2.0 planning archive — kept for historical reference",
}


def is_excluded(path_rel: str) -> bool:
    return any(path_rel.startswith(prefix) for prefix in EXCLUDE_PATH_PREFIXES)


def should_scan_refs(path_rel: str) -> bool:
    # Historical plans are kept as targets for provenance, but their outgoing
    # links often point to superseded scratch files. They should not break the
    # current repository health gate.
    return not (
        path_rel.startswith("docs/plans/archive/")
        or path_rel.startswith("assets/experience-bank/raw/")
    )


def find_md_files(root: Path):
    files = []
    for path in root.rglob("*.md"):
        rel = path.relative_to(root).as_posix()
        if is_excluded(rel):
            continue
        files.append(path)
    return sorted(files)


def extract_sections(text: str):
    return {m.group(1).strip() for m in SECTION_PATTERN.finditer(text)}


def normalize_target(target: str, source_file: Path, all_files: set):
    """Resolve a reference string to an absolute path under repo root."""
    # 1) Treat as repo-root-relative
    p1 = (REPO_ROOT / target).resolve()
    if p1 in all_files:
        return p1

    # 2) Treat as relative to source file's directory
    p2 = (source_file.parent / target).resolve()
    if p2 in all_files:
        return p2

    # 3) Basename match
    basename = Path(target).name
    matches = [f for f in all_files if f.name == basename]
    if len(matches) == 1:
        return matches[0]
    if matches:
        return min(matches, key=lambda f: len(set(f.parts) ^ set(source_file.parts)))

    return None


def detect_cycles(graph):
    """Tarjan SCC. Returns list of cycles (each cycle is a list of nodes)."""
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    on_stack = set()
    cycles = []

    sys.setrecursionlimit(10000)

    def strongconnect(node):
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        for successor in graph.get(node, []):
            if successor not in index:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in on_stack:
                lowlinks[node] = min(lowlinks[node], index[successor])
        if lowlinks[node] == index[node]:
            component = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == node:
                    break
            if len(component) > 1 or (len(component) == 1 and component[0] in graph.get(component[0], [])):
                cycles.append(component)

    for node in list(graph.keys()):
        if node not in index:
            strongconnect(node)
    return cycles


def main():
    md_files = find_md_files(REPO_ROOT)
    file_set = set(f.resolve() for f in md_files)
    file_to_sections = {f.resolve(): extract_sections(f.read_text(encoding="utf-8", errors="replace")) for f in md_files}

    refs_out = defaultdict(list)
    refs_in = defaultdict(set)
    dead_refs = []

    for f in md_files:
        if not should_scan_refs(f.relative_to(REPO_ROOT).as_posix()):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        seen_in_this_file = set()
        for m in REF_PATTERN.finditer(text):
            raw_target = m.group(1)
            section = m.group(2)
            target_path = normalize_target(raw_target, f, file_set)
            if target_path is None:
                key = (f.resolve(), raw_target)
                if key not in seen_in_this_file:
                    dead_refs.append((f.resolve(), raw_target, "file_not_found"))
                    seen_in_this_file.add(key)
                continue
            if target_path == f.resolve():
                continue  # ignore self-refs
            # Section validation
            if section and len(section) >= 2:
                target_sections = file_to_sections.get(target_path, set())
                section_normalized = section.strip().lower().rstrip("：:")
                # Skip range-style refs like "2-3" or "3-§5" — these refer to multiple sections
                is_range = bool(re.search(r'[-–—]', section_normalized))
                if is_range:
                    continue
                section_found = any(section_normalized in h.lower() for h in target_sections)
                if not section_found and len(section_normalized) >= 3:
                    dead_refs.append((f.resolve(), f"{raw_target} §{section}", "section_not_found"))
            refs_out[f.resolve()].append((target_path, section, raw_target))
            refs_in[target_path].add(f.resolve())

    graph = {src: list({t for t, _, _ in tgts}) for src, tgts in refs_out.items()}
    all_cycles = detect_cycles(graph)
    short_cycles = [c for c in all_cycles if len(c) <= SHORT_CYCLE_MAX_NODES]
    long_cycles = [c for c in all_cycles if len(c) > SHORT_CYCLE_MAX_NODES]

    ENTRY_POINTS = {
        "README.md", "CLAUDE.md", "SKILL.md", "VERSION_LOG.md", "VERSIONING.md",
        "MODULES.md", "MEMORY.md",
    }
    orphans = []
    allowed_orphans_seen = []
    for f in md_files:
        if f.resolve() in refs_in:
            continue
        if f.name in ENTRY_POINTS:
            continue
        rel_parts = f.relative_to(REPO_ROOT).parts
        if "plans" in rel_parts:
            continue
        if "decisions" in rel_parts:
            continue
        if "archive" in rel_parts:
            continue
        rel_path = str(f.relative_to(REPO_ROOT))
        if rel_path in ALLOWED_ORPHANS:
            allowed_orphans_seen.append((rel_path, ALLOWED_ORPHANS[rel_path]))
            continue
        orphans.append(f)

    fan_out = sorted(refs_in.items(), key=lambda kv: len(kv[1]), reverse=True)

    rel = lambda p: str(Path(p).relative_to(REPO_ROOT))

    print(f"=== Methodology Cross-Reference Analysis ===\n")
    print(f"Files scanned: {len(md_files)}")
    total_refs = sum(len(v) for v in refs_out.values())
    print(f"Cross-references found: {total_refs}\n")

    print(f"--- SHORT CIRCULAR REFERENCES (SCC ≤{SHORT_CYCLE_MAX_NODES}) ---")
    if not short_cycles:
        print("  (none found)\n")
    else:
        for i, cycle in enumerate(short_cycles, 1):
            names = " -> ".join(rel(n) for n in cycle) + f" -> {rel(cycle[0])}"
            print(f"  Cycle {i}: {names}")
        print()

    if long_cycles:
        print(f"--- LARGE SCC (size > {SHORT_CYCLE_MAX_NODES}, treated as healthy doc-cross-link webs) ---")
        for c in long_cycles:
            print(f"  SCC of {len(c)} nodes (info only, not a bug)")
        print()

    print(f"--- DEAD REFERENCES ---")
    if not dead_refs:
        print("  (none found)\n")
    else:
        for src, raw, reason in dead_refs[:50]:
            print(f"  {rel(src)} -> {raw}  [{reason}]")
        if len(dead_refs) > 50:
            print(f"  ... ({len(dead_refs) - 50} more)")
        print()

    print(f"--- ORPHAN FILES (no inbound refs, excluding entry points / plans / decisions / archive) ---")
    if not orphans:
        print("  (none found)\n")
    else:
        for f in orphans:
            print(f"  {rel(f)}")
        print()

    if allowed_orphans_seen:
        print(f"--- ALLOWED ORPHANS (intentional, see ALLOWED_ORPHANS in script) ---")
        for path, reason in allowed_orphans_seen:
            print(f"  {path}")
            print(f"    reason: {reason}")
        print()

    print(f"--- TOP 10 INBOUND FAN-OUT (most-referenced) ---")
    for tgt, sources in fan_out[:10]:
        print(f"  {rel(tgt):60s} <- {len(sources)} refs")
    print()

    print(f"--- TOP 10 OUTBOUND FAN-OUT (most-referencing) ---")
    out_counts = sorted(((src, len({t for t, _, _ in tgts})) for src, tgts in refs_out.items()),
                        key=lambda kv: kv[1], reverse=True)
    for src, count in out_counts[:10]:
        print(f"  {rel(src):60s} -> {count} refs")
    print()

    health = []
    if short_cycles:
        health.append(f"{len(short_cycles)} short circular refs")
    real_dead = [d for d in dead_refs if d[2] == "file_not_found"]
    if real_dead:
        health.append(f"{len(real_dead)} dead file refs")
    if orphans:
        health.append(f"{len(orphans)} orphan files")
    if health:
        print(f"=== HEALTH: warnings ({'; '.join(health)}) ===")
        sys.exit(1 if short_cycles or real_dead else 0)
    else:
        print(f"=== HEALTH: clean ===")


if __name__ == "__main__":
    main()
