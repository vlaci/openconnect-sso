BOLD   = \033[1m
RED    = \033[31m
GREEN  = \033[32m
YELLOW = \033[33m
RESET  = \033[0m

NIX_QTWRAPPER ?= # Set up environment for locating Qt libraries from Nix

all: help

###############################################################################
## General
.PHONY: help
help:  ## Show possible make targets
ifeq (, $(shell which gawk))
 $(error "This target requires 'gawk'. Install that first.")
endif
	@echo -e "Usage: $(YELLOW)make$(RESET) $(GREEN)<target>$(RESET)"
	@gawk 'match($$0, /^## (.+)$$/, m) { \
		printf "\n$(BOLD)%s targets:$(RESET)\n", m[1]; \
	}; \
	match($$0, /^([^:]+)\s*:\s*[^#=]+## +(.*)/, m) { \
		if (length(m[1]) < 10) { \
			printf "  $(YELLOW)%-10s$(RESET) %s\n", m[1], m[2]; \
		} else { \
			printf "$(YELLOW)%s$(RESET)\n%-12s %s\n", m[1], "", m[2]; \
		};\
	}; \
	' $(MAKEFILE_LIST)


.PHONY: dev
dev:  ## Initializes repository for development
	@echo -e "$(BOLD)-> Setting up pre-commit hooks...$(RESET)"
	pre-commit install --install-hooks

	@echo -e "$(BOLD)-> Removing existing .venv directory if exists...$(RESET)"
	rm -fr .venv

	@echo -e "$(BOLD)-> Creating virtualenv in .venv...$(RESET)"
	python3 -m venv .venv

	@echo -e "$(BOLD)-> Installing openconnect-sso in develop mode...$(RESET)"
	source .venv/bin/activate && poetry install

	@echo -e "$(BOLD)$(YELLOW)=> Development installation finished.$(RESET)"

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
	$(NIX_QTWRAPPER) pytest
