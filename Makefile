# mywater_localisation — operator entrypoint for the Lokalise round-trip.
#
# Thin, human-friendly wrapper over the token-holding scripts the operator runs by
# hand. One token-free exception lives here on purpose: `make apply` is the serialized
# single-writer fan-in (per-language /tmp/loc_<lang>.json -> corpus), kept as one
# operator command so parallel per-language applies can't race ([CR-CORPUS-CONCURRENCY]):
#
#   Lokalise  ──pull──▶  strings.ndjson  ──push──▶  Lokalise  ──export──▶  iOS/Android/server
#
# `pull` regenerates the corpus FROM Lokalise and OVERWRITES local edits, so it is
# gated behind a typed confirmation (the others are already --apply-gated upstream).
# Run with the token in the env: LOKALISE_API_TOKEN, LOKALISE_PROJECT_ID.

SHELL := /bin/bash

# PY: venv holding the Lokalise token / requirements.  PY3: stdlib-only, token-free (lint / qa).
PY     ?= .venv-lokalise/bin/python
PY3    ?= python3
CORPUS ?= strings.ndjson
GLOSSARY ?= glossary.ndjson

# Passthrough to push / export, e.g.  make push ARGS="--lang de"  /  make export ARGS="ios"
ARGS ?=
# Explicit Lokalise key deletion inputs. Prefer DELETE_KEY_IDS for migrations: ids
# survive key-name drift and avoid deleting a newly-created replacement with a
# similar name. DELETE_KEYS_FILE is line-delimited; kind is "name" or "id".
DELETE_KEY_IDS ?=
DELETE_KEY_NAMES ?=
DELETE_KEYS_FILE ?=
DELETE_KEYS_FILE_KIND ?= name

.DEFAULT_GOAL := help
.PHONY: help pull push push-dry delete-keys delete-keys-dry export export-dry glossary-pull glossary-push glossary-push-dry lint diff apply

help:
	@printf '%s\n' \
	"mywater_localisation — operator commands (Lokalise token holder only)" \
	"" \
	"  Pipeline:  Lokalise  --pull-->  $(CORPUS)  --push-->  Lokalise  --export-->  iOS/Android/server" \
	"" \
	"  make pull         Загрузка из Lokalise — regenerate $(CORPUS) FROM Lokalise." \
	"                    OVERWRITES the local corpus (asks for confirmation). FORCE=1 skips the prompt." \
	"  make push-dry     Выгрузка (план) — dry-run of corpus -> Lokalise import. ARGS=\"--lang de\"." \
	"  make push         Выгрузка — push dirty corpus edits -> Lokalise (--apply). ARGS=\"--key foo\"." \
	"  make delete-keys-dry  Удаление ключей (план) — dry-run Lokalise delete-keys." \
	"  make delete-keys      Удаление ключей — PERMANENT delete in Lokalise (--apply)." \
	"                    DELETE_KEY_IDS=\"123 456\" or DELETE_KEY_NAMES=\"oldKey\"." \
	"  make export-dry   Экспорт (план) — dry-run Lokalise -> platform repos. ARGS=\"ios\"." \
	"  make export       Экспорт — download Lokalise -> iOS/Android/server repos (--apply)." \
	"" \
	"  Glossary API: Lokalise glossary  --glossary-pull-->  $(GLOSSARY)  --glossary-push-->  Lokalise glossary" \
	"  make glossary-pull      Download Lokalise glossary -> $(GLOSSARY)." \
	"                          OVERWRITES the local glossary (asks for confirmation). FORCE=1 skips the prompt." \
	"  make glossary-push-dry  Dry-run local glossary -> Lokalise glossary API upsert." \
	"  make glossary-push      Push local glossary -> Lokalise glossary API (--apply)." \
	"" \
	"  make apply        Fan-in — применить /tmp/loc_<lang>.json в корпус, по одному (token-free)." \
	"                    Единый сериализованный писатель (без гонки applies). LANGS=\"vi nb de\"." \
	"  make lint         Token-free QA: placeholder lint + value hygiene (run before push)." \
	"  make diff         git diff of $(CORPUS) (review edits before push)." \
	"" \
	"  Workflow:  (agents emit /tmp/loc_<lang>.json)  ->  make apply LANGS=\"…\"  ->  make diff  ->  make push" \
	"" \
	"  Vars: ARGS=… passthrough to push/export/glossary; FORCE=1 skips pull confirmations;" \
	"        LANGS=… space-separated languages for make apply; PY=… overrides the venv python ($(PY))."

# Lokalise -> corpus. DESTRUCTIVE to local edits: it rewrites $(CORPUS) wholesale,
# discarding any un-imported translation / metadata edits. Confirmation-gated so it
# is never run by accident; FORCE=1 bypasses for automation.
pull:
	@printf '%s\n' \
	"------------------------------------------------------------------" \
	"  make pull — regenerate $(CORPUS) FROM Lokalise." \
	"  This OVERWRITES the local corpus. Any un-imported local edits" \
	"  (translations / metadata not yet pushed) will be LOST." \
	"  Correct order:  edit -> make diff -> make push -> then make pull." \
	"------------------------------------------------------------------"
	@if ! git diff --quiet HEAD -- $(CORPUS) 2>/dev/null; then \
	  echo "!! WARNING: $(CORPUS) has UNCOMMITTED changes — exactly the un-imported"; \
	  echo "!! edits that regenerate will discard. Run 'make push' (and commit) first."; \
	  echo ""; \
	fi
	@if [ "$(FORCE)" = "1" ]; then \
	  echo "FORCE=1 — skipping confirmation."; \
	  $(PY) loc_corpus_ndjson.py; \
	else \
	  printf 'Type "yes" to OVERWRITE the local corpus from Lokalise: '; \
	  read -r ans; \
	  if [ "$$ans" = "yes" ]; then \
	    $(PY) loc_corpus_ndjson.py; \
	  else \
	    echo "Aborted — corpus unchanged."; \
	  fi; \
	fi

# corpus -> Lokalise. Dry-run (default) is token-runnable evidence; --apply mutates.
push-dry:
	$(PY) loc_corpus_import.py $(ARGS)

push:
	$(PY) loc_corpus_import.py $(ARGS) --apply

delete-keys-dry:
	@set -e; \
	args=""; \
	for id in $(DELETE_KEY_IDS); do args="$$args --key-id $$id"; done; \
	for name in $(DELETE_KEY_NAMES); do args="$$args --key-name $$name"; done; \
	if [ -n "$(DELETE_KEYS_FILE)" ]; then args="$$args --keys-file $(DELETE_KEYS_FILE) --keys-file-kind $(DELETE_KEYS_FILE_KIND)"; fi; \
	if [ -z "$$args" ]; then \
	  echo 'usage: make delete-keys-dry DELETE_KEY_IDS="123 456"'; \
	  echo '   or: make delete-keys-dry DELETE_KEY_NAMES="oldKey anotherOldKey"'; \
	  echo '   or: make delete-keys-dry DELETE_KEYS_FILE=/tmp/keys.txt DELETE_KEYS_FILE_KIND=id'; \
	  exit 2; \
	fi; \
	$(PY) lokalise_helper.py delete-keys $$args

delete-keys:
	@set -e; \
	args=""; \
	for id in $(DELETE_KEY_IDS); do args="$$args --key-id $$id"; done; \
	for name in $(DELETE_KEY_NAMES); do args="$$args --key-name $$name"; done; \
	if [ -n "$(DELETE_KEYS_FILE)" ]; then args="$$args --keys-file $(DELETE_KEYS_FILE) --keys-file-kind $(DELETE_KEYS_FILE_KIND)"; fi; \
	if [ -z "$$args" ]; then \
	  echo 'usage: make delete-keys DELETE_KEY_IDS="123 456"'; \
	  echo '   or: make delete-keys DELETE_KEY_NAMES="oldKey anotherOldKey"'; \
	  echo '   or: make delete-keys DELETE_KEYS_FILE=/tmp/keys.txt DELETE_KEYS_FILE_KIND=id'; \
	  exit 2; \
	fi; \
	$(PY) lokalise_helper.py delete-keys $$args --apply

# Lokalise -> platform repos. Dry-run prints the resolved plan token-free; --apply downloads.
export-dry:
	$(PY) loc_export.py $(ARGS)

export:
	$(PY) loc_export.py $(ARGS) --apply

# Lokalise glossary -> local terminology source of truth. Destructive for local
# unpushed glossary edits, so confirmation-gated like `make pull`.
glossary-pull:
	@printf '%s\n' \
	"------------------------------------------------------------------" \
	"  make glossary-pull — regenerate $(GLOSSARY) FROM Lokalise glossary." \
	"  This OVERWRITES the local terminology glossary. Any unpushed local" \
	"  glossary edits will be LOST." \
	"  Correct order:  edit -> git diff -- $(GLOSSARY) -> make glossary-push -> then make glossary-pull." \
	"------------------------------------------------------------------"
	@if ! git diff --quiet HEAD -- $(GLOSSARY) 2>/dev/null; then \
	  echo "!! WARNING: $(GLOSSARY) has UNCOMMITTED changes — exactly the unpushed"; \
	  echo "!! edits that regenerate will discard. Run 'make glossary-push' (and commit) first."; \
	  echo ""; \
	fi
	@if [ "$(FORCE)" = "1" ]; then \
	  echo "FORCE=1 — skipping confirmation."; \
	  $(PY) loc_glossary_ndjson.py --out $(GLOSSARY) $(ARGS); \
	else \
	  printf 'Type "yes" to OVERWRITE the local glossary from Lokalise: '; \
	  read -r ans; \
	  if [ "$$ans" = "yes" ]; then \
	    $(PY) loc_glossary_ndjson.py --out $(GLOSSARY) $(ARGS); \
	  else \
	    echo "Aborted — glossary unchanged."; \
	  fi; \
	fi

# local terminology source of truth -> Lokalise glossary. Dry-run is token-free
# validation/plan; --apply resolves project language ids and upserts through API.
glossary-push-dry:
	$(PY3) loc_glossary_import.py --glossary $(GLOSSARY) $(ARGS)

glossary-push:
	$(PY) loc_glossary_import.py --glossary $(GLOSSARY) $(ARGS) --apply

# Token-free review gates (same lints loc_corpus_import pre-flights).
lint:
	$(PY3) loc_placeholder_lint.py
	$(PY3) loc_qa.py

diff:
	@git diff -- $(CORPUS)

# Serialized single-writer fan-in (token-free): apply per-language translation
# artifacts /tmp/loc_<lang>.json into $(CORPUS), ONE AT A TIME in a single process.
# Routing every apply through this one operator command IS the "single writer" — it
# structurally avoids the concurrent read-mutate-write race that silently clobbers
# translations (CLAUDE.md [CR-CORPUS-CONCURRENCY] / PIPELINE.md § Parallel translation passes).
# Parallel fan-out agents only EMIT the artifacts; a clean `git diff --stat` is NOT a
# substitute lock. Usage:  make apply LANGS="vi"  /  make apply LANGS="vi nb de"
apply:
	@if [ -z "$(LANGS)" ]; then \
	  echo 'usage: make apply LANGS="vi"   (or LANGS="vi nb de")'; \
	  echo 'applies /tmp/loc_<lang>.json into $(CORPUS), one language at a time'; \
	  exit 2; \
	fi
	@for l in $(LANGS); do \
	  f="/tmp/loc_$$l.json"; \
	  if [ ! -f "$$f" ]; then echo "!! missing artifact $$f - skipping $$l"; continue; fi; \
	  echo "==> apply $$l  <-  $$f"; \
	  $(PY3) loc_apply_lang.py "$$l" "$$f" --corpus $(CORPUS) || exit 1; \
	done
	@echo "Review: make diff   then push: make push"
