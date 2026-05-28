#!/usr/bin/env python3
"""Download Lokalise exports straight into each platform repo (iOS / Android / server).

The third leg of the pipeline (after loc_corpus_ndjson.py pulls and
loc_corpus_import.py pushes):

    strings.ndjson + Lokalise --export--> iOS .strings / Android .xml / server JSON

Until now that export was clicked by hand in the Lokalise "Download" UI — dozens of
toggles per platform, plus per-language code overrides, that are easy to get wrong
(README.md "Export from Lokalise" documents them). This script encodes those
validated settings as per-platform profiles and drives the download API, so the
settings live in one reviewable place instead of a human's memory. Each `params`
entry below maps 1:1 to a documented README setting; that table stays the
human-readable spec this script implements.

Flow (per platform, under --apply):
  queue async export (POST /files/async-download) -> poll the process to 'finished'
  -> fetch the .zip bundle -> unzip to /tmp -> apply local code renames
  (Android `values-en/` -> `values/`) -> run sanity checks on the STAGED tree ->
  only if clean, place files into the repo's resource dirs (never a half-broken
  bundle). The repo is left as an unstaged git diff for the operator to review and
  commit — same diff-review discipline as the rest of the pipeline.

Token discipline (CLAUDE.md [CR-SECRETS] / [CR-ACCESS]): the default is a DRY RUN
that prints the fully-resolved params, language mapping and target paths with no
token and no network — the agent-runnable review artifact. --apply performs the
download + write and needs LOKALISE_API_TOKEN, so it is operator-run. The download
only READS Lokalise; the only mutation is writing files into the platform repos.

Language codes: the corpus uses Lokalise isos (pt_BR, zh_CN, es, id); each platform
ships a different code (iOS pt-BR/zh-Hans; Android pt-rBR/zh-rCN/es-rES/in + the
base `values/`; server es_ES, and no Arabic). The `language_mapping` per profile
owns that translation; a post-download sanity check asserts the produced language
set matches what each profile expects, so a mapping drift fails loudly instead of
silently shipping a mis-named file. The expected set is derived from the corpus
language list (strings.meta.json), so adding a project language is picked up
automatically.

Runs under the venv (needs the python-lokalise-api SDK + requests; see
requirements.txt). A dry run / --help works under plain python3 (requests is
imported lazily, only for the actual bundle fetch):

    .venv-lokalise/bin/python loc_export.py                 # dry-run, all platforms
    .venv-lokalise/bin/python loc_export.py ios --apply     # download iOS into the repo
    .venv-lokalise/bin/python loc_export.py --to /tmp/exp --apply   # write to /tmp (test)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Run as a file; keep sibling imports working regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import DEFAULT_CORPUS  # noqa: E402
from lokalise_helper import (  # noqa: E402
    DEFAULT_BASE_URL,
    LokaliseClient,
    LokaliseConfig,
    LokaliseError,
)

DEFAULT_META = DEFAULT_CORPUS.with_name(DEFAULT_CORPUS.stem + ".meta.json")

# Settings shared by every platform profile. Each maps to a README "Export from
# Lokalise" setting and is identical across the three documented tables:
#   export_empty_as=base   -> "Empty translations: Replace with base language"
#   export_sort=a_z        -> "Sort keys by: Key name A-Z"
#   include_description     -> "Include description: off"
#   include_comments        -> "Include comments: off"
#   disable_references=False-> "Disable referencing: off"
#   all_platforms=False     -> "Include all platform keys: off" (export only the
#                              keys assigned to this format's platform)
BASE_PARAMS: dict[str, Any] = {
    "export_empty_as": "base",
    "export_sort": "a_z",
    "include_description": False,
    "include_comments": False,
    "disable_references": False,
    "all_platforms": False,
}


@dataclass(frozen=True)
class Platform:
    name: str
    fmt: str  # Lokalise download `format` code (strings / xml / json)
    params: dict[str, Any]  # static download params (excl. format/filter_langs/language_mapping)
    language_mapping: dict[str, str]  # corpus iso -> export code (only the overrides)
    exclude_langs: frozenset[str]  # corpus isos NOT exported on this platform
    repo_env: str  # env var overriding the repo root
    repo_default: Path
    dest_subdir: str  # resource dir under the repo where files land


# --- iOS: Apple Strings (README "iOS — Apple Strings", validated 2026-05-27) ----
# Multiple files per language (assigned filenames) so InfoPlist.strings splits from
# Localizable.strings and plurals land in Localizable.stringsdict; directory prefix
# %LANG_ISO%.lproj. placeholder_format=ios converts [%s]->%@ etc.; escape_percent
# ships the canonical literal [%] as %% (safe under R.swift String(format:)).
IOS = Platform(
    name="ios",
    fmt="strings",
    params={
        **BASE_PARAMS,
        "original_filenames": True,  # "File structure: Multiple files (use assigned filenames)"
        "directory_prefix": "%LANG_ISO%.lproj",
        "placeholder_format": "ios",  # "Placeholder format: iOS"
        "escape_percent": True,  # "Convert all [%] to %%: on"
        "indentation": "2sp",  # "Indentation: 2 spaces"
        "replace_breaks": True,  # "Replace line breaks with \\n: on"
        "add_newline_eof": True,  # "Add new line at EOF: on"
    },
    language_mapping={"pt_BR": "pt-BR", "zh_CN": "zh-Hans"},
    exclude_langs=frozenset(),
    repo_env="MYWATER_IOS_REPO",
    repo_default=Path("/Users/viktor/git/mywater_ios"),
    dest_subdir="water/Supporting Files/Localization",
)

# --- Android: XML (README "Android — XML", settings finalized 2026-05-27) --------
# One file per language (no InfoPlist analogue) -> values-%LANG_ISO%/strings.xml.
# placeholder_format=printf converts [%s]->%s, [%i]->%d; escape_percent ships [%]
# as %% (aapt needs %% for a literal percent in a formatted string). The English
# base must end up in the un-prefixed values/ dir; Lokalise can only emit
# values-en/, so we rename it locally after download (see stage_android).
ANDROID = Platform(
    name="android",
    fmt="xml",
    params={
        **BASE_PARAMS,
        "original_filenames": False,  # "File structure: One file per language"
        "bundle_structure": "values-%LANG_ISO%/strings.xml",
        "placeholder_format": "printf",  # "Placeholder format: Printf"
        "escape_percent": True,  # "Convert all [%] to %%: on"
        "indentation": "2sp",  # "Indentation: 2 spaces"
        "replace_breaks": True,  # "Replace line breaks with \\n: on"
    },
    language_mapping={"es": "es-rES", "id": "in", "pt_BR": "pt-rBR", "zh_CN": "zh-rCN"},
    exclude_langs=frozenset(),
    repo_env="MYWATER_ANDROID_REPO",
    repo_default=Path("/Users/viktor/git/mywater_android"),
    dest_subdir="modules/resources/lib-strings/src/main/res",
)

# --- server: flat JSON (README "server — JSON", validated 2026-05-28) ------------
# Flat {key: value} (format=json, NOT json_structured). Arabic is excluded — the
# server ships no ar.json and falls back to en. Spanish file is es_ES.json.
# escape_percent off: server strings are not run through sprintf, so a literal %
# stays %. Server strings have no placeholders today (printf if ever).
SERVER = Platform(
    name="server",
    fmt="json",
    params={
        **BASE_PARAMS,
        "original_filenames": False,
        "bundle_structure": "%LANG_ISO%.json",
        "placeholder_format": "printf",
        "escape_percent": False,  # "Convert all [%] to %%: off"
        "indentation": "4sp",  # "Indentation: 4 spaces"
        "add_newline_eof": True,  # repo convention: JSON files end with a trailing newline
    },
    language_mapping={"es": "es_ES"},
    exclude_langs=frozenset({"ar"}),
    repo_env="MYWATER_SERVER_REPO",
    repo_default=Path("/Users/viktor/git/mywater_server"),
    dest_subdir="resources/locale",
)

PLATFORMS: dict[str, Platform] = {p.name: p for p in (IOS, ANDROID, SERVER)}


def main() -> int:
    args = build_parser().parse_args()
    try:
        langs = read_corpus_langs(args.meta)
        platforms = [PLATFORMS[name] for name in args.platforms]

        if not args.apply:
            print(
                "DRY RUN: resolved export plan (no token, no download, no write). "
                "Pass --apply to execute.\n"
            )
            for platform in platforms:
                print_plan(platform, langs, dest_dir_for(platform, args))
                print()
            return 0

        config = config_from_args(args)
        client = LokaliseClient(config)
        all_ok = True
        for platform in platforms:
            dest = dest_dir_for(platform, args)
            ensure_dest(platform, dest, args)
            ok = export_platform(
                client,
                platform,
                langs,
                dest,
                poll_timeout=args.poll_timeout,
                http_timeout=args.timeout,
                run_sanity=not args.no_sanity,
            )
            all_ok = all_ok and ok
        if all_ok:
            print("\nDone. Review each repo (git status / git diff) before committing.")
            return 0
        print("\nOne or more platforms failed sanity checks; see errors above.", file=sys.stderr)
        return 1
    except LokaliseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download Lokalise exports into each platform repo (iOS / Android / server)."
    )
    parser.add_argument(
        "platforms",
        nargs="*",
        choices=tuple(PLATFORMS),
        default=list(PLATFORMS),
        help="Platforms to export. Default: all three.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Download and write the files. Without this, prints the resolved plan (token-free).",
    )
    parser.add_argument(
        "--to",
        type=Path,
        default=None,
        help="Write under DIR/<platform>/ instead of the platform repo (safe testing).",
    )
    parser.add_argument(
        "--no-sanity",
        action="store_true",
        help="Skip the post-download sanity checks (not recommended).",
    )
    parser.add_argument("--ios-repo", type=Path, default=None, help="Override the iOS repo root.")
    parser.add_argument("--android-repo", type=Path, default=None, help="Override the Android repo root.")
    parser.add_argument("--server-repo", type=Path, default=None, help="Override the server repo root.")
    parser.add_argument(
        "--meta",
        default=str(DEFAULT_META),
        help=f"Corpus meta JSON (for the language list). Default: {DEFAULT_META}.",
    )
    parser.add_argument("--project-id", default=os.environ.get("LOKALISE_PROJECT_ID"), help="Lokalise project id. Defaults to LOKALISE_PROJECT_ID.")
    parser.add_argument("--branch", default=os.environ.get("LOKALISE_BRANCH"), help="Optional Lokalise branch. Defaults to LOKALISE_BRANCH.")
    parser.add_argument("--base-url", default=os.environ.get("LOKALISE_API_BASE", DEFAULT_BASE_URL), help=f"API base URL. Defaults to {DEFAULT_BASE_URL}.")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("LOKALISE_TIMEOUT", "60")), help="HTTP timeout (API + bundle fetch) in seconds.")
    parser.add_argument("--poll-timeout", type=float, default=300.0, help="Max seconds to wait for an async export to finish.")
    return parser


def config_from_args(args: argparse.Namespace) -> LokaliseConfig:
    api_token = os.environ.get("LOKALISE_API_TOKEN")
    if not api_token:
        raise LokaliseError("LOKALISE_API_TOKEN is required for --apply; pass secrets via env, not CLI args.")
    if not args.project_id:
        raise LokaliseError("project id is required via --project-id or LOKALISE_PROJECT_ID.")
    return LokaliseConfig(
        api_token=api_token,
        project_id=args.project_id,
        branch=args.branch,
        base_url=args.base_url,
        timeout_seconds=args.timeout,
    )


def read_corpus_langs(meta_path: str) -> list[str]:
    path = Path(meta_path)
    if not path.is_file():
        raise LokaliseError(f"corpus meta not found: {path} (regenerate with loc_corpus_ndjson.py)")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise LokaliseError(f"invalid meta JSON {path}: {error}") from error
    langs = data.get("languages")
    if not isinstance(langs, list) or not langs or not all(isinstance(item, str) for item in langs):
        raise LokaliseError(f"meta {path} has no usable 'languages' list")
    return langs


def build_download_params(platform: Platform, langs: list[str]) -> tuple[dict[str, Any], list[str]]:
    """Resolve the full download payload for a platform plus the list of exported
    corpus isos. `filter_langs` uses ORIGINAL project isos (set only when languages
    are dropped); `language_mapping` overrides the export code for the listed isos."""
    params = dict(platform.params)
    params["format"] = platform.fmt
    included = [lang for lang in langs if lang not in platform.exclude_langs]
    if platform.exclude_langs:
        params["filter_langs"] = included
    mapping = [
        {"original_language_iso": src, "custom_language_iso": platform.language_mapping[src]}
        for src in sorted(platform.language_mapping)
        if src in included
    ]
    if mapping:
        params["language_mapping"] = mapping
    return params, included


def export_codes(platform: Platform, included: list[str]) -> list[str]:
    """The per-language code each file ships under (after language_mapping)."""
    return [platform.language_mapping.get(lang, lang) for lang in included]


def repo_root_for(platform: Platform, args: argparse.Namespace) -> Path:
    override = getattr(args, f"{platform.name}_repo")
    root = override or Path(os.environ.get(platform.repo_env, str(platform.repo_default)))
    return Path(root).expanduser()


def dest_dir_for(platform: Platform, args: argparse.Namespace) -> Path:
    if args.to is not None:
        return Path(args.to).expanduser() / platform.name
    return repo_root_for(platform, args) / platform.dest_subdir


def ensure_dest(platform: Platform, dest: Path, args: argparse.Namespace) -> None:
    if args.to is not None:
        dest.mkdir(parents=True, exist_ok=True)
        return
    if not dest.is_dir():
        raise LokaliseError(
            f"[{platform.name}] localization dir not found: {dest} "
            f"(set --{platform.name}-repo or {platform.repo_env})"
        )


def print_plan(platform: Platform, langs: list[str], dest: Path) -> None:
    params, included = build_download_params(platform, langs)
    codes = export_codes(platform, included)
    print(f"=== {platform.name} ===")
    print(f"  dest:      {dest}")
    print(f"  languages: {len(included)} -> {', '.join(codes)}")
    print(f"  params:    {json.dumps(params, ensure_ascii=False, sort_keys=True)}")


def export_platform(
    client: LokaliseClient,
    platform: Platform,
    langs: list[str],
    dest: Path,
    *,
    poll_timeout: float,
    http_timeout: float,
    run_sanity: bool,
) -> bool:
    params, included = build_download_params(platform, langs)
    codes = export_codes(platform, included)
    print(f"[{platform.name}] queuing async export ({len(included)} languages)...")
    content = run_download(client, platform, params, poll_timeout=poll_timeout, http_timeout=http_timeout)

    with tempfile.TemporaryDirectory(prefix=f"loc_export_{platform.name}_") as tmp:
        root = Path(tmp)
        extract_bundle(content, root)
        staged = STAGERS[platform.name](root)
        if not staged:
            print(f"[{platform.name}] bundle contained no expected files — skipping.", file=sys.stderr)
            return False

        issues = VALIDATORS[platform.name](staged, codes) if run_sanity else []
        warnings = [msg for level, msg in issues if level == "warn"]
        errors = [msg for level, msg in issues if level == "error"]
        for msg in warnings:
            print(f"[{platform.name}] warning: {msg}", file=sys.stderr)
        if errors:
            print(f"[{platform.name}] SANITY FAILED — repo NOT modified ({len(errors)} error(s)):", file=sys.stderr)
            for msg in errors:
                print(f"  - {msg}", file=sys.stderr)
            return False

        written = place(staged, dest)
    print(f"[{platform.name}] wrote {len(written)} file(s) -> {dest}")
    return True


def run_download(
    client: LokaliseClient,
    platform: Platform,
    params: dict[str, Any],
    *,
    poll_timeout: float,
    http_timeout: float,
) -> bytes:
    process = client.submit_async_download(params)
    process_id = process.get("process_id")
    if not process_id:
        raise LokaliseError(f"[{platform.name}] async export returned no process_id: {process}")
    url = poll_download(client, process_id, timeout=poll_timeout)
    return fetch_bundle(url, http_timeout)


def poll_download(client: LokaliseClient, process_id: str, *, timeout: float, interval: float = 2.0) -> str:
    deadline = time.monotonic() + timeout
    while True:
        process = client.get_process(process_id)
        status = str(process.get("status") or "").lower()
        if status == "finished":
            url = bundle_url(process.get("details"))
            if not url:
                raise LokaliseError(f"export finished but no bundle url in details: {process.get('details')!r}")
            return url
        if status in {"failed", "cancelled", "queued_failed", "error"}:
            detail = process.get("message") or process.get("details")
            raise LokaliseError(f"async export {status}: {detail}")
        if time.monotonic() > deadline:
            raise LokaliseError(f"async export timed out after {timeout:.0f}s (last status {status!r})")
        time.sleep(interval)


def bundle_url(details: Any) -> str | None:
    if not isinstance(details, dict):
        return None
    for key in ("download_url", "bundle_url", "url", "file_url"):
        value = details.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def fetch_bundle(url: str, timeout: float) -> bytes:
    import requests  # lazy: keeps dry-run / --help working without the dependency

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as error:
        raise LokaliseError(f"failed to fetch bundle: {error}") from error
    return response.content


def extract_bundle(content: bytes, dest: Path) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            archive.extractall(dest)
    except zipfile.BadZipFile as error:
        raise LokaliseError(f"downloaded bundle is not a valid zip: {error}") from error


# --- staging: discover the relevant files in the unzipped bundle ----------------
# Each returns a list of (source_file, target_rel) where target_rel is the path
# under the platform's dest dir. rglob (not a fixed root) tolerates any wrapper
# folder Lokalise may add around the bundle.


def stage_ios(root: Path) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for lproj in sorted(root.rglob("*.lproj")):
        if not lproj.is_dir():
            continue
        for item in sorted(lproj.iterdir()):
            if item.is_file():
                out.append((item, f"{lproj.name}/{item.name}"))
    return out


def stage_android(root: Path) -> list[tuple[Path, str]]:
    # The English base exports as values-en/; rename it to the un-prefixed values/
    # (the required default fallback). Lokalise cannot emit values/ directly.
    out: list[tuple[Path, str]] = []
    for xml in sorted(root.rglob("strings.xml")):
        parent = xml.parent.name
        if parent != "values" and not parent.startswith("values-"):
            continue
        target_dir = "values" if parent == "values-en" else parent
        out.append((xml, f"{target_dir}/strings.xml"))
    return out


def stage_server(root: Path) -> list[tuple[Path, str]]:
    return [(path, path.name) for path in sorted(root.rglob("*.json"))]


STAGERS: dict[str, Callable[[Path], list[tuple[Path, str]]]] = {
    "ios": stage_ios,
    "android": stage_android,
    "server": stage_server,
}


# --- sanity checks: validate the STAGED tree before it touches a repo -----------
# Each returns a list of (level, message); level "error" blocks placement (the
# repo is left untouched), "warn" is reported but allows placement.


def diff_set(label: str, expected: set[str], produced: set[str]) -> list[str]:
    out: list[str] = []
    missing = sorted(expected - produced)
    extra = sorted(produced - expected)
    if missing:
        out.append(f"missing {label}(s): {', '.join(missing)}")
    if extra:
        out.append(f"unexpected {label}(s): {', '.join(extra)}")
    return out


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def validate_ios(staged: list[tuple[Path, str]], codes: list[str]) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    dirs = {rel.split("/", 1)[0] for _src, rel in staged}
    issues += [("error", msg) for msg in diff_set("lproj dir", {f"{code}.lproj" for code in codes}, dirs)]
    counts: dict[str, int] = {}
    for src, rel in staged:
        name = rel.rsplit("/", 1)[-1]
        counts[name] = counts.get(name, 0) + 1
        text = read_text(src)
        if "[%" in text:
            issues.append(("error", f"{rel}: unconverted universal placeholder '[%'"))
        if name.endswith(".strings"):
            if '= "";' in text:
                issues.append(("warn", f"{rel}: blank value(s) present (expected base-language fill)"))
            if "/*" in text:
                issues.append(("warn", f"{rel}: comment block present (include_description should be off)"))
    for fname in ("Localizable.strings", "InfoPlist.strings", "Localizable.stringsdict"):
        if counts.get(fname, 0) != len(codes):
            issues.append(("warn", f"{fname}: found {counts.get(fname, 0)}, expected {len(codes)}"))
    return issues


def validate_android(staged: list[tuple[Path, str]], codes: list[str]) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    dirs = {rel.split("/", 1)[0] for _src, rel in staged}
    expected = {"values" if code == "en" else f"values-{code}" for code in codes}
    issues += [("error", msg) for msg in diff_set("values dir", expected, dirs)]
    if "values" not in dirs:
        issues.append(("error", "missing default values/ (English base rename failed)"))
    has_plurals = False
    for src, rel in staged:
        text = read_text(src)
        if "[%" in text:
            issues.append(("error", f"{rel}: unconverted universal placeholder '[%'"))
        if "%@" in text or "%#@" in text:
            issues.append(("error", f"{rel}: iOS-only placeholder leaked (%@ / %#@)"))
        if "<plurals" in text:
            has_plurals = True
    if not has_plurals:
        issues.append(("warn", "no <plurals> in any file (expected some plural keys)"))
    return issues


def validate_server(staged: list[tuple[Path, str]], codes: list[str]) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    files = {rel for _src, rel in staged}
    issues += [("error", msg) for msg in diff_set("json file", {f"{code}.json" for code in codes}, files)]
    if "ar.json" in files:
        issues.append(("error", "ar.json present (server excludes Arabic)"))
    for src, rel in staged:
        text = read_text(src)
        if "[%" in text:
            issues.append(("error", f"{rel}: unconverted universal placeholder '[%'"))
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            issues.append(("error", f"{rel}: invalid JSON ({error})"))
            continue
        if not isinstance(data, dict):
            issues.append(("error", f"{rel}: not a flat JSON object"))
    return issues


VALIDATORS: dict[str, Callable[[list[tuple[Path, str]], list[str]], list[tuple[str, str]]]] = {
    "ios": validate_ios,
    "android": validate_android,
    "server": validate_server,
}


def place(staged: list[tuple[Path, str]], dest: Path) -> list[str]:
    written: list[str] = []
    for src, rel in staged:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        written.append(rel)
    return written


if __name__ == "__main__":
    raise SystemExit(main())
