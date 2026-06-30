.PHONY: check check-local-bindings

check:
	python3 scripts/validate_fixtures.py

check-local-bindings:
	python3 scripts/validate_bindings.py
