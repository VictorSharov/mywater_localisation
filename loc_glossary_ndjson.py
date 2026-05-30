#!/usr/bin/env python3
"""Regenerate `glossary.ndjson` from the Lokalise glossary via API.

This is the download/pull edge for terminology. It overwrites the local glossary
path through `loc_glossary.write_records`, so the Makefile target wraps it in a
typed confirmation just like `make pull` does for `strings.ndjson`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import loc_glossary as glossary  # noqa: E402
from loc_glossary_api import (  # noqa: E402
    add_lokalise_api_args,
    api_term_to_record,
    config_from_args,
    glossary_path_display,
    language_maps,
)
from lokalise_helper import LokaliseClient, LokaliseError  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download Lokalise glossary terms into glossary.ndjson.")
    parser.add_argument("--out", type=Path, default=glossary.DEFAULT_GLOSSARY, help=f"Output glossary path. Default: {glossary.DEFAULT_GLOSSARY}.")
    add_lokalise_api_args(parser)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        client = LokaliseClient(config_from_args(args))
        _iso_to_id, id_to_iso = language_maps(client)
        terms = client.list_glossary_terms()
        records = [api_term_to_record(item, id_to_iso) for item in terms]
        issues = glossary.validate_records(records)
        errors = [issue for issue in issues if issue[0] == "error"]
        for level, name, message in issues:
            print(f"{level}: {name}: {message}")
        if errors:
            print(f"refusing: {len(errors)} downloaded glossary validation error(s); local file unchanged.", file=sys.stderr)
            return 1
        glossary.write_records(args.out, records)
        print(f"wrote {len(records)} glossary term(s) -> {glossary_path_display(args.out)}")
        return 0
    except LokaliseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
