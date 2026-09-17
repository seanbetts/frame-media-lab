.PHONY: test check doctor android media synthetic verify-source
PYTHON ?= python3

test:
	@mkdir -p build/tmp
	TMPDIR="$(CURDIR)/build/tmp" $(PYTHON) -m unittest discover -s tests -v

check: test
	$(PYTHON) scripts/check_sources.py
	@if command -v ruff >/dev/null 2>&1; then RUFF_CACHE_DIR=build/ruff-cache ruff check lab scripts tests; else echo "NOT TESTED: optional Ruff lint (not installed)"; fi

doctor:
	./frame-media-lab doctor

android:
	./frame-media-lab build-android

media:
	./frame-media-lab generate-media

synthetic:
	./frame-media-lab --synthetic l1 first-hour

verify-source:
	./frame-media-lab verify-source
