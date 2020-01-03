.PHONY: version test clean

version:
	@echo "__version__ = \"$$(git describe --tags)\"" >openconnect_sso/version.py

test:
	pytest

clean:
	rm -f .coverage.*
	rm -rf openconnect_sso.egg-info
	rm -rf .pytest_cache
