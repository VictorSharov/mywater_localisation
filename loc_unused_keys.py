#!/usr/bin/env python3
"""Find statically unused localization key candidates.

This is a report-only scan. It lives in the shared localisation repo and scans
the iOS repo (--repo-root, default /Users/viktor/git/mywater_ios) and the Android
repo (--android-repo): localization pools, generated R.swift accessors, source
references, and Android string resources, then writes separate key-name lists
suitable for `lokalise_helper.py add-tags --keys-file ... --skip-missing`.

The result is a static candidate set, not deletion proof: App Store metadata,
remote push/config payloads, SDK consoles, and other out-of-repo consumers can
still reference localization keys.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import stat
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from lokalise_helper import DEFAULT_ANDROID_REPO, LokaliseError, collect_android_usage


# Paths below are relative to the iOS repo root (--repo-root); this scanner now
# lives in the shared localisation repo, so the iOS repo is an explicit input.
DEFAULT_IOS_REPO = Path(os.environ.get("MYWATER_IOS_REPO", "/Users/viktor/git/mywater_ios"))
LOCALIZATION_ROOT = Path("water/Supporting Files/Localization")
WIDGET_ROOT = Path("widgetNew")
GENERATED_ROOT = Path("water/Supporting Files/Generated")
# venv + helper live next to this script in the localisation repo root.
SCRIPT_DIR = Path(__file__).resolve().parent
LOKALISE_VENV_PYTHON = Path(".venv-lokalise/bin/python")
LOKALISE_HELPER = Path("lokalise_helper.py")
DEFAULT_IOS_UNUSED_TAG = "ios_unused"
DEFAULT_ANDROID_UNUSED_TAG = "android_unused"

LOCALIZATION_POOLS = (
    ("Localizable.strings", LOCALIZATION_ROOT, "Localizable.strings"),
    ("Localizable.stringsdict", LOCALIZATION_ROOT, "Localizable.stringsdict"),
    ("InfoPlist.strings", LOCALIZATION_ROOT, "InfoPlist.strings"),
    ("widget14.strings", WIDGET_ROOT, "widget14.strings"),
)

GENERATED_R_FILES = (
    GENERATED_ROOT / "R.generated.swift",
    GENERATED_ROOT / "R.WidgetIOS.generated.swift",
    GENERATED_ROOT / "R.WidgetWatchOS.generated.swift",
    GENERATED_ROOT / "R.watchkitapp.generated.swift",
)

SOURCE_ROOTS = (
    ("water", Path("water")),
    ("widgetNew", Path("widgetNew")),
    ("watchOS", Path("watchOS")),
    ("DrinkReminderNotificationContentExtension", Path("DrinkReminderNotificationContentExtension")),
    ("waterTests", Path("waterTests")),
)

EXTRA_SOURCE_FILES = (
    ("project", Path("water.xcodeproj/project.pbxproj")),
    ("project", Path("Podfile")),
)

SOURCE_SUFFIXES = {
    ".entitlements",
    ".h",
    ".intentdefinition",
    ".json",
    ".m",
    ".mm",
    ".pbxproj",
    ".plist",
    ".storyboard",
    ".swift",
    ".xib",
    ".xcconfig",
    ".yaml",
    ".yml",
}
SOURCE_NAMES = {"Podfile"}
EXCLUDED_DIR_NAMES = {
    ".build",
    ".git",
    "build",
    "Carthage",
    "DerivedData",
    "Pods",
}

TABLE_STRUCT_TO_POOL = {
    "infoPlist": {"InfoPlist.strings"},
    "localizable": {"Localizable.strings", "Localizable.stringsdict"},
    "widget14": {"widget14.strings"},
}

GENERATED_ACCESSOR_RE = re.compile(
    r'\b(?:var|func)\s+([A-Za-z_][A-Za-z0-9_]*)\b.*?'
    r'\.init\(key:\s*"((?:\\.|[^"\\])*)",\s*tableName:\s*"([^"]+)"'
)
TYPED_R_RE = re.compile(
    r"\bR\s*\.\s*string(?:\s*\([^)]*\))?\s*\.\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\b",
    re.S,
)
OWNER_ACCESSOR_RE = re.compile(r"\bstrings\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\b")
LOCALIZABLE_CLOSURE_ACCESSOR_RE = re.compile(r"\$0\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\b")
SWIFT_STRING_RE = re.compile(r'"((?:\\.|[^"\\])*)"')
XML_VALUE_RE = re.compile(r"<(?:key|string)>([^<]+)</(?:key|string)>")

# `SpotlightNavItem.rawValue` is interpolated into keys at runtime.
KNOWN_DYNAMIC_KEYS = {
    "spotlightNavDescription_statistics",
    "spotlightNavDescription_beverages",
    "spotlightNavDescription_settings",
    "spotlightNavDescription_reminders",
    "spotlightNavDescription_friends",
    "spotlightNavDescription_caffeine",
    "spotlightNavDescription_alcohol",
}


PoolKey = tuple[str, str]


class ScanError(RuntimeError):
    """Raised when the repository cannot be scanned safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_IOS_REPO, help=f"iOS repo root. Default: {DEFAULT_IOS_REPO} or MYWATER_IOS_REPO.")
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp"), help="Directory for reports. Default: /tmp.")
    parser.add_argument(
        "--output-prefix",
        default=f"mywater_unused_localization_{dt.date.today().isoformat()}",
        help="Output file prefix. Default: mywater_unused_localization_<today>.",
    )
    parser.add_argument(
        "--tag",
        dest="ios_tag",
        default=DEFAULT_IOS_UNUSED_TAG,
        help="Deprecated alias for --ios-tag.",
    )
    parser.add_argument(
        "--ios-tag",
        default=DEFAULT_IOS_UNUSED_TAG,
        help=f"Tag used for iOS-unused candidates. Default: {DEFAULT_IOS_UNUSED_TAG}.",
    )
    parser.add_argument(
        "--android-tag",
        default=DEFAULT_ANDROID_UNUSED_TAG,
        help=f"Tag used for Android-unused candidates. Default: {DEFAULT_ANDROID_UNUSED_TAG}.",
    )
    parser.add_argument(
        "--android-repo",
        type=Path,
        default=Path(os.environ.get("MYWATER_ANDROID_REPO", str(DEFAULT_ANDROID_REPO))),
        help=(
            "Android repo used for the independent android_unused scan. "
            f"Default: {DEFAULT_ANDROID_REPO} or MYWATER_ANDROID_REPO."
        ),
    )
    parser.add_argument(
        "--exclude-tests",
        action="store_true",
        help="Do not scan waterTests. Tests are included by default because they can be the only typed references.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()

    try:
        entries = collect_localization_entries(repo_root)
        key_to_pool_keys = group_key_names(entries)
        generated = collect_generated_accessors(repo_root, entries)
        source_files, source_counts = collect_source_files(repo_root, include_tests=not args.exclude_tests)
        used = collect_used_pool_keys(repo_root, source_files, key_to_pool_keys, generated)
        android_unused_key_names, android_source_counts = collect_android_unused_key_names(args.android_repo)

        for key in KNOWN_DYNAMIC_KEYS:
            for pool_key in key_to_pool_keys.get(key, ()):
                used[pool_key].add("known-dynamic:SpotlightNavItem.rawValue")

        output_files, counts = write_reports(
            repo_root=repo_root,
            output_dir=output_dir,
            prefix=args.output_prefix,
            ios_tag=args.ios_tag,
            android_tag=args.android_tag,
            entries=entries,
            key_to_pool_keys=key_to_pool_keys,
            used=used,
            android_unused_key_names=android_unused_key_names,
            android_source_counts=android_source_counts,
            source_counts=source_counts,
        )
    except ScanError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    summary = {
        **counts,
        "source_files_by_root": source_counts,
        "output_files": {name: str(path) for name, path in output_files.items()},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def collect_localization_entries(repo_root: Path) -> dict[PoolKey, dict[str, Any]]:
    entries: dict[PoolKey, dict[str, Any]] = {}
    for pool_name, base_rel, file_name in LOCALIZATION_POOLS:
        base = repo_root / base_rel
        if not base.exists():
            continue

        for path in sorted(base.glob(f"*.lproj/{file_name}")):
            data = read_plutil_dict(path)
            locale = path.parent.name.removesuffix(".lproj")
            rel_path = relative_path(repo_root, path)

            for key in sorted(data):
                pool_key = (pool_name, key)
                info = entries.setdefault(pool_key, {"locales": set(), "paths": []})
                info["locales"].add(locale)
                info["paths"].append(rel_path)

    if not entries:
        raise ScanError(f"no localization entries found under {LOCALIZATION_ROOT}")
    return entries


def read_plutil_dict(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["plutil", "-convert", "json", "-o", "-", str(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise ScanError(f"plutil failed for {path}: {result.stderr.strip()}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ScanError(f"plutil produced invalid JSON for {path}: {error}") from error

    if not isinstance(data, dict):
        raise ScanError(f"plutil JSON root is not an object for {path}")
    return data


def group_key_names(entries: dict[PoolKey, dict[str, Any]]) -> dict[str, set[PoolKey]]:
    grouped: dict[str, set[PoolKey]] = defaultdict(set)
    for pool_key in entries:
        pool, key = pool_key
        grouped[key].add((pool, key))
    return grouped


def collect_generated_accessors(
    repo_root: Path,
    entries: dict[PoolKey, dict[str, Any]],
) -> dict[tuple[str, str], set[PoolKey]]:
    accessors: dict[tuple[str, str], set[PoolKey]] = defaultdict(set)
    entry_keys = set(entries)

    for rel_path in GENERATED_R_FILES:
        path = repo_root / rel_path
        if not path.exists():
            continue

        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                match = GENERATED_ACCESSOR_RE.search(line)
                if not match:
                    continue

                accessor, raw_key, table_name = match.groups()
                key = decode_string_literal(raw_key)
                table_struct = table_struct_name(table_name)
                pool_names = TABLE_STRUCT_TO_POOL.get(table_struct, set())
                for pool_name in pool_names:
                    pool_key = (pool_name, key)
                    if pool_key in entry_keys:
                        accessors[(table_struct, accessor)].add(pool_key)

    return accessors


def table_struct_name(table_name: str) -> str:
    if table_name == "InfoPlist":
        return "infoPlist"
    if table_name == "Localizable":
        return "localizable"
    return table_name[:1].lower() + table_name[1:]


def collect_source_files(repo_root: Path, *, include_tests: bool) -> tuple[list[Path], dict[str, int]]:
    seen: set[Path] = set()
    files: list[Path] = []
    counts: dict[str, int] = {}

    for label, rel_root in SOURCE_ROOTS:
        if label == "waterTests" and not include_tests:
            counts[label] = 0
            continue

        root = repo_root / rel_root
        count = 0
        if root.exists():
            for path in sorted(root.rglob("*")):
                if is_source_candidate(repo_root, path) and path not in seen:
                    seen.add(path)
                    files.append(path)
                    count += 1
        counts[label] = count

    extra_count = 0
    for _, rel_path in EXTRA_SOURCE_FILES:
        path = repo_root / rel_path
        if is_source_candidate(repo_root, path) and path not in seen:
            seen.add(path)
            files.append(path)
            extra_count += 1
    counts["extra"] = extra_count

    return files, counts


def is_source_candidate(repo_root: Path, path: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    rel_parts = path.relative_to(repo_root).parts
    if any(part in EXCLUDED_DIR_NAMES or part.endswith(".xcassets") for part in rel_parts):
        return False
    if path.suffix in {".strings", ".stringsdict"}:
        return False
    if path.name.startswith("R.") and path.name.endswith(".generated.swift"):
        return False
    return path.suffix in SOURCE_SUFFIXES or path.name in SOURCE_NAMES


def collect_used_pool_keys(
    repo_root: Path,
    source_files: list[Path],
    key_to_pool_keys: dict[str, set[PoolKey]],
    generated: dict[tuple[str, str], set[PoolKey]],
) -> dict[PoolKey, set[str]]:
    used: dict[PoolKey, set[str]] = defaultdict(set)

    for path in source_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel_path = relative_path(repo_root, path)

        # Intentionally scan raw source text, including commented-out R.string
        # references. This script produces Lokalise deletion/tag candidates, not
        # deletion proof; a commented reference can be uncommented later, so keep
        # that key out of the safe candidate list.
        for table_struct, accessor in TYPED_R_RE.findall(text):
            for pool_key in generated.get((table_struct, accessor), ()):
                used[pool_key].add(f"{rel_path}:R.string.{table_struct}.{accessor}")

        for accessor in OWNER_ACCESSOR_RE.findall(text):
            for pool_key in generated.get(("localizable", accessor), ()):
                used[pool_key].add(f"{rel_path}:strings.{accessor}")

        if "_R.string.localizable" in text:
            for accessor in LOCALIZABLE_CLOSURE_ACCESSOR_RE.findall(text):
                for pool_key in generated.get(("localizable", accessor), ()):
                    used[pool_key].add(f"{rel_path}:localizable-closure.{accessor}")

        for literal in extract_literals(text):
            for pool_key in literal_pool_keys(path, literal, key_to_pool_keys):
                used[pool_key].add(f"{rel_path}:literal")

    return used


def collect_android_unused_key_names(android_repo: Path) -> tuple[list[str], dict[str, int]]:
    try:
        android_usage = collect_android_usage(android_repo)
    except LokaliseError as error:
        raise ScanError(str(error)) from error

    unused_key_names = sorted(android_usage.defined_keys - android_usage.used_keys, key=str.lower)
    source_counts = {
        "defined_keys": len(android_usage.defined_keys),
        "used_keys": len(android_usage.used_keys),
        "unused_keys": len(unused_key_names),
    }
    return unused_key_names, source_counts


def literal_pool_keys(
    path: Path,
    literal: str,
    key_to_pool_keys: dict[str, set[PoolKey]],
) -> set[PoolKey]:
    pool_keys = key_to_pool_keys.get(literal, set())
    if not pool_keys:
        return set()

    allowed_pools = literal_allowed_pools(path)
    return {pool_key for pool_key in pool_keys if pool_key[0] in allowed_pools}


def literal_allowed_pools(path: Path) -> set[str]:
    suffix = path.suffix
    if suffix == ".intentdefinition":
        return {"widget14.strings"}
    if suffix == ".plist":
        return {"InfoPlist.strings"}
    if suffix in {".storyboard", ".xib"}:
        return {"Localizable.strings", "Localizable.stringsdict"}

    return {"Localizable.strings", "Localizable.stringsdict"}


def extract_literals(text: str) -> set[str]:
    literals: set[str] = set()
    for raw in SWIFT_STRING_RE.findall(text):
        literals.add(raw)
        literals.add(decode_string_literal(raw))
    for value in XML_VALUE_RE.findall(text):
        stripped = value.strip()
        if stripped:
            literals.add(stripped)
    return literals


def decode_string_literal(raw: str) -> str:
    try:
        return json.loads(f'"{raw}"')
    except json.JSONDecodeError:
        return raw


def write_reports(
    *,
    repo_root: Path,
    output_dir: Path,
    prefix: str,
    ios_tag: str,
    android_tag: str,
    entries: dict[PoolKey, dict[str, Any]],
    key_to_pool_keys: dict[str, set[PoolKey]],
    used: dict[PoolKey, set[str]],
    android_unused_key_names: list[str],
    android_source_counts: dict[str, int],
    source_counts: dict[str, int],
) -> tuple[dict[str, Path], dict[str, int]]:
    output_dir.mkdir(parents=True, exist_ok=True)

    unused_pool_keys = {pool_key for pool_key in entries if pool_key not in used}
    safe_unused_key_names = sorted(
        key for key, pool_keys in key_to_pool_keys.items() if pool_keys and pool_keys <= unused_pool_keys
    )
    unsafe_duplicate_names = sorted(
        key
        for key, pool_keys in key_to_pool_keys.items()
        if len({pool for pool, _ in pool_keys}) > 1
        and any(pool_key in unused_pool_keys for pool_key in pool_keys)
        and not pool_keys <= unused_pool_keys
    )

    output_files = {
        "ios_candidates_tsv": output_dir / f"{prefix}_ios_candidates.tsv",
        "ios_key_names": output_dir / f"{prefix}_ios_key_names.txt",
        "android_candidates_tsv": output_dir / f"{prefix}_android_candidates.tsv",
        "android_key_names": output_dir / f"{prefix}_android_key_names.txt",
        "report_json": output_dir / f"{prefix}_report.json",
        "duplicate_pool_review_tsv": output_dir / f"{prefix}_duplicate_pool_review.tsv",
        "ios_add_tag_dry_run_sh": output_dir / f"{prefix}_ios_add_tag_dry_run.sh",
        "android_add_tag_dry_run_sh": output_dir / f"{prefix}_android_add_tag_dry_run.sh",
    }

    write_candidates_tsv(output_files["ios_candidates_tsv"], entries, unused_pool_keys, safe_unused_key_names)
    write_key_names(repo_root, output_files["ios_key_names"], safe_unused_key_names, ios_tag)
    write_android_candidates_tsv(output_files["android_candidates_tsv"], android_unused_key_names)
    write_key_names(repo_root, output_files["android_key_names"], android_unused_key_names, android_tag)
    write_duplicate_pool_review(
        output_files["duplicate_pool_review_tsv"],
        key_to_pool_keys,
        unused_pool_keys,
        safe_unused_key_names,
    )
    write_dry_run_script(repo_root, output_files["ios_add_tag_dry_run_sh"], output_files["ios_key_names"], ios_tag)
    write_dry_run_script(
        repo_root,
        output_files["android_add_tag_dry_run_sh"],
        output_files["android_key_names"],
        android_tag,
    )

    pool_counts = defaultdict(int)
    unused_pool_counts = defaultdict(int)
    for pool, _ in entries:
        pool_counts[pool] += 1
    for pool, _ in unused_pool_keys:
        unused_pool_counts[pool] += 1

    counts = {
        "entries_total": len(entries),
        "keys_total_unique_names": len(key_to_pool_keys),
        "source_files_scanned": sum(source_counts.values()),
        "unused_entries": len(unused_pool_keys),
        "ios_unused_key_names": len(safe_unused_key_names),
        "android_unused_key_names": len(android_unused_key_names),
        "unsafe_duplicate_pool_names": len(unsafe_duplicate_names),
    }
    report = {
        **counts,
        "android": android_source_counts,
        "pools": dict(sorted(pool_counts.items())),
        "unused_by_pool": dict(sorted(unused_pool_counts.items())),
        "unsafe_duplicate_pool_names": unsafe_duplicate_names,
        "note": (
            "Static source scan only. Review vendor/runtime consumers before tagging "
            "or deleting localization keys."
        ),
        "output_files": {name: str(path) for name, path in output_files.items()},
    }
    output_files["report_json"].write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return output_files, counts


def write_candidates_tsv(
    path: Path,
    entries: dict[PoolKey, dict[str, Any]],
    unused_pool_keys: set[PoolKey],
    safe_unused_key_names: list[str],
) -> None:
    safe_names = set(safe_unused_key_names)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("key_name", "pool", "locales", "paths", "safe_to_tag_by_key_name"))
        for pool, key in sorted(unused_pool_keys, key=lambda item: (item[0], item[1].lower())):
            info = entries[(pool, key)]
            writer.writerow(
                (
                    key,
                    pool,
                    ",".join(sorted(info["locales"])),
                    ";".join(info["paths"]),
                    "yes" if key in safe_names else "no",
                )
            )


def write_android_candidates_tsv(path: Path, android_unused_key_names: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("key_name", "safe_to_tag_by_key_name"))
        for key in android_unused_key_names:
            writer.writerow((key, "yes"))


def write_key_names(repo_root: Path, path: Path, safe_unused_key_names: list[str], tag: str) -> None:
    lines = [
        "# Static unused localization key candidates from loc_unused_keys.py.",
        "# Review out-of-repo runtime consumers before applying tags or deleting keys.",
        f"# Dry run: {lokalise_helper_command(repo_root, path, tag)}",
    ]
    lines.extend(safe_unused_key_names)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_duplicate_pool_review(
    path: Path,
    key_to_pool_keys: dict[str, set[PoolKey]],
    unused_pool_keys: set[PoolKey],
    safe_unused_key_names: list[str],
) -> None:
    safe_names = set(safe_unused_key_names)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("key_name", "status", "pools", "unused_pools", "used_pools", "safe_to_tag_by_key_name"))
        for key, pool_keys in sorted(key_to_pool_keys.items()):
            pools = sorted({pool for pool, _ in pool_keys})
            if len(pools) <= 1:
                continue

            unused_pools = sorted(pool for pool, _ in pool_keys if (pool, key) in unused_pool_keys)
            used_pools = sorted(pool for pool, _ in pool_keys if (pool, key) not in unused_pool_keys)
            if unused_pools and used_pools:
                status = "mixed"
            elif unused_pools:
                status = "all_unused"
            else:
                status = "all_used"
            writer.writerow(
                (
                    key,
                    status,
                    ",".join(pools),
                    ",".join(unused_pools),
                    ",".join(used_pools),
                    "yes" if key in safe_names else "no",
                )
            )


def write_dry_run_script(repo_root: Path, path: Path, keys_file: Path, tag: str) -> None:
    script = "\n".join(
        [
            "#!/bin/sh",
            "set -eu",
            "# Mutating helper commands are dry-run by default.",
            "# Add --apply after reviewing the dry-run output.",
            lokalise_helper_command(repo_root, keys_file, tag),
            "",
        ]
    )
    path.write_text(script, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def lokalise_helper_command(repo_root: Path, keys_file: Path, tag: str) -> str:
    # venv + helper live in the localisation repo (next to this script), not the
    # scanned iOS repo_root — resolve them from SCRIPT_DIR.
    venv_python = SCRIPT_DIR / LOKALISE_VENV_PYTHON
    helper = SCRIPT_DIR / LOKALISE_HELPER
    return (
        f"{shell_quote(venv_python)} {shell_quote(helper)} add-tags "
        f"--keys-file {shell_quote(keys_file)} --skip-missing --tag {shell_quote(tag)}"
    )


def shell_quote(path_or_value: Path | str) -> str:
    value = str(path_or_value)
    if re.fullmatch(r"[A-Za-z0-9_./:+@%=-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def relative_path(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
