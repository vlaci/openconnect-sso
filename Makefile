NIX_QTWRAPPER ?= # Set up environment for locating Qt libraries from Nix
CONTINUE_ON_ERROR ?= # should be used only for testing

.ONESHELL:
SHELL = bash
.SHELLFLAGS = -euo pipefail -c
.DEFAULT_GOAL :=

BOLD   = \033[1m
RED    = \033[31m
GREEN  = \033[32m
YELLOW = \033[33m
RESET  = \033[0m

echo-stage   = printf "$(BOLD)-> %s$(RESET)\n"
echo-warn    = printf "$(BOLD)$(YELLOW)-> %s$(RESET)\n"
echo-success = printf "$(BOLD)$(GREEN)=> %s$(RESET)\n"
error-exit   = err_exit () { printf "$(BOLD)$(RED)=> %s$(RESET)\n" "$$1"; $(if $(CONTINUE_ON_ERROR),$(echo-warn) "Overriding error",exit 1); }; err_exit

###############################################################################
## General
.PHONY: help
help:  ## Show this help message
#
# From https://gist.github.com/vlaci/304110986bad60ac87513b189503e21a
# Parses help message from Makefile. Messages must appear after target or
# variable specification. Descriptions must start with at least one whitespace
# character and followed by `##` characters. If global variables section is not
# needed, remove or comment out its section.
#
# Suggested Makefile layout:
#   GLOBAL_VARIABLES ?= dummy  ## Global variables
#   PRIVATE_VARIABLE ?= private  # No help shown here
#   ...
#
#   ## Section header
#   help: ## Show this help message
#       ...
#
#   ## Another section
#   target:  ## Shows target description
#       ...
#   target: TARGET_SPECIFIC ?=  ## This description appears at target's help
#
ifeq (, $(shell which gawk))
 $(error "This target requires 'gawk'. Install that first.")
endif
	@echo -e "Usage: $(BOLD)make$(RESET) $(YELLOW)<target>$(RESET) [$(GREEN)VARIABLE$(RESET)=value, ...]"
#	@echo
#	@echo -e "$(BOLD)Global variables:$(RESET)"
	gawk 'match($$0, /^## (.+)$$/, m) {
		printf "\n$(BOLD)%s targets:$(RESET)\n", m[1]
	}
	match($$0, /^([^: ]+)\s*:\s*[^#=]+## +(.*)/, m) {
		if (length(m[1]) < 10) {
			printf "  $(YELLOW)%-10s$(RESET) %s\n", m[1], m[2]
		} else {
			printf "  $(YELLOW)%s$(RESET)\n%-12s %s\n", m[1], "", m[2]
		}
	}
	match($$0, /^([^?= ]+)\s*\?=\s*([^# ]+)?\s*## +(.*)/, m) {
		if (length(m[2]) == 0) {
			m[2] = "unset"
		}
		printf "  $(GREEN)%s$(RESET): %s (default: $(BOLD)%s$(RESET))\n", m[1], m[3], m[2]
	}
	match($$0, /^[^: ]+\s*:\s*([^?= ]+)\s*\?=\s*([^# ]+)?\s*## +(.*)/, m) {
		if (length(m[2]) == 0) {
			m[2] = "unset"
		}
		printf "%-13s- $(GREEN)%s$(RESET): %s (default: $(BOLD)%s$(RESET))\n", "", m[1], m[3], m[2]
	}
	' $(MAKEFILE_LIST)

.PHONY: dev
dev:  ## Initializes repository for development
	@$(echo-stage) "Setting up pre-commit hooks..."
	pre-commit install --install-hooks

	$(echo-stage) "Removing existing .venv directory if exists..."
	rm -fr .venv

	$(echo-stage) "Creating virtualenv in .venv..."
	python3 -m venv .venv

	$(echo-stage) "Installing openconnect-sso in develop mode..."
	source .venv/bin/activate && poetry install

	$(echo-success) "Development installation finished."

.PHONY: clean
clean:  ## Remove temporary files and artifacts
	git clean -Xdf

###############################################################################
## QA
.PHONY: check
check: pre-commit test  ## Run required tests and coding style checks

.PHONY: pre-commit
pre-commit:
	pre-commit run -a

.PHONY: test
test:  ## Run tests
	$(NIX_QTWRAPPER) .venv/bin/pytest

###############################################################################
## Release
VERSION = $(shell .venv/bin/python -c 'import openconnect_sso; print(f"v{openconnect_sso.__version__}")')

.PHONY: changelog
changelog:  ## Shows the project's changelog
	trap "rm -f .reno_err" EXIT
	{ reno report $(if $(ONLY_CURRENT),\
		--earliest-version=$$(git describe --abbrev=0 --tags)
	) 2> .reno_err || cat .reno_err
	} | pandoc --from rst --to $(FORMAT) $(if $(OUTPUT_FILE),-o $(OUTPUT_FILE))
changelog: FORMAT ?= gfm  ## Output format for changelog
changelog: ONLY_CURRENT ?=  ## Log only current (and unreleased) versions changes
changelog: OUTPUT_FILE ?=  ## Write changelog to file instead of displaying

.INTERMEDIATE: CHANGELOG.md
CHANGELOG.md: $(wildcard releasenotes/**/*)
	$(MAKE) changelog OUTPUT_FILE=CHANGELOG.md

.PHONY: dist
dist: CHANGELOG.md  ## Build packages from whatever state the repository is
	poetry build
	cp CHANGELOG.md dist/CHANGELOG-$(VERSION).md

.PHONY: tag-repo
tag-repo: CURRENT_TAG = $(shell git describe --tags)
tag-repo:
	@$(echo-stage) "Tagging repository as $(VERSION)"
	if [ "$(VERSION)" != "$(CURRENT_TAG)" ]; then
		git tag $(VERSION) || { $(error-exit) "Existing tag $(VERSION) is not at HEAD!"; }
	fi

release: before-release before-clean clean dev check tag-repo dist  ## Build release version in a clean environment
	@$(echo-success) "Finished building release version $(VERSION)"

before-clean:
	@echo -en "$(YELLOW)"
	git clean --dry-run -Xd
	echo -e "$(RESET)"
	$(echo-stage) "CTRL-C in 10s to cancel..."
	sleep 10

before-release:
	@$(echo-stage) "Building release version..."
	if [ -n "$$(git status --short)" ]; then
		git status
		$(error-exit) "Repository is dirty!"
	fi
	if [ $$(git rev-parse HEAD) != $$(git rev-parse origin/master) ]; then
		git --no-pager log --oneline --graph origin/master...
		$(error-exit) "HEAD must point to origin/master!"
	fi
