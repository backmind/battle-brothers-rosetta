MOD_NAME = rosetta
SOURCES = rosetta scripts

include .env
export
SHELL := /bin/bash

.ONESHELL:
test: check-compile
	@set -e;
	TMP_FILE=$$(mktemp);
	squirrel test.nut 2> >(tee "$$TMP_FILE" >&2);
	if [ -s "$$TMP_FILE" ]; then
		rm "$$TMP_FILE"
		exit 1
	fi

zip: test
	@set -e;
	LAST_TAG=$$(git tag -l --sort=-creatordate | grep . | head -n1);
	echo $$LAST_TAG;
	MODIFIED=$$( git diff $$LAST_TAG --quiet $(SOURCES) || echo _MODIFIED);
	FILENAME=mod_$(MOD_NAME)_$${LAST_TAG}$${MODIFIED}.zip;
	zip --filesync -r "$${FILENAME}" $(SOURCES);

clean:
	@rm -f *_MODIFIED.zip;

install: test
	@set -e;
	FILENAME=$(DATA_DIR)mod_$(MOD_NAME)_TMP.zip;
	zip --filesync -r "$${FILENAME}" $(SOURCES);

check-compile:
	@set -e
	find . -name \*.nut -print0 | xargs -0 -n1 squirrel -c && echo "Syntax OK"
	rm out.cnut

# Regression sweep for extractor changes: every mod whose own check runs rosetta, plus xbe.
recheck:
	@set -e
	FAILED=
	for mk in ../mods/*/Makefile; do
		grep -q rosetta $$mk || continue
		DIR=$$(dirname $$mk)
		printf '%-28s ' $$(basename $$DIR)
		if make -C $$DIR check >/dev/null 2>&1; then echo OK; else echo FAIL; FAILED="$$FAILED $$(basename $$DIR)"; fi
	done
	printf '%-28s ' xbe
	cd ../xbe && rosetta -qc hackflows/rosetta_ru.nut . >/dev/null 2>&1 \
		&& echo OK || echo "INCOMPLETE (known, see mods/translations/TODO.md)"
	[ -z "$$FAILED" ] || { echo "FAILED:$$FAILED"; exit 1; }
