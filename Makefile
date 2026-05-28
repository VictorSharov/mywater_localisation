# mywater_localisation — operator entrypoint for the Lokalise round-trip.
#
# Thin, human-friendly wrapper over the three token-holding scripts the operator
# runs by hand (the apply scripts agents run are token-free and stay out of here):
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

# Passthrough to push / export, e.g.  make push ARGS="--lang de"  /  make export ARGS="ios"
ARGS ?=

.DEFAULT_GOAL := help
.PHONY: help pull push push-dry export export-dry lint diff

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
	"  make export-dry   Экспорт (план) — dry-run Lokalise -> platform repos. ARGS=\"ios\"." \
	"  make export       Экспорт — download Lokalise -> iOS/Android/server repos (--apply)." \
	"" \
	"  make lint         Token-free QA: placeholder lint + value hygiene (run before push)." \
	"  make diff         git diff of $(CORPUS) (review edits before push)." \
	"" \
	"  Vars: ARGS=… passthrough to push/export; FORCE=1 skips the pull confirmation;" \
	"        PY=… overrides the venv python ($(PY))."

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

# Lokalise -> platform repos. Dry-run prints the resolved plan token-free; --apply downloads.
export-dry:
	$(PY) loc_export.py $(ARGS)

export:
	$(PY) loc_export.py $(ARGS) --apply

# Token-free review gates (same lints loc_corpus_import pre-flights).
lint:
	$(PY3) loc_placeholder_lint.py
	$(PY3) loc_qa.py

diff:
	@git diff -- $(CORPUS)
